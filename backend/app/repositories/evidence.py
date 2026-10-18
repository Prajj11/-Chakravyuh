"""SQLite evidence metadata and atomic append-only ingestion/audit transactions."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app.config import Parameters
from app.evidence.canonical import canonical_bytes, sha256
from app.evidence.store import EvidenceStore, IntegrityMismatch
from app.schemas.models import AuditTrailEntry, DataOrigin, UnifiedSocialEvent

DDL = """
CREATE TABLE IF NOT EXISTS parameter_sets (
 parameter_set_id TEXT PRIMARY KEY, parameter_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_artifacts (
 artifact_id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, kind TEXT NOT NULL,
 mime_type TEXT NOT NULL, size INTEGER NOT NULL, origin TEXT NOT NULL, scope TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
 event_id TEXT PRIMARY KEY, collector_id TEXT NOT NULL, raw_payload_sha256 TEXT NOT NULL,
 source_event_key TEXT NOT NULL, origin TEXT NOT NULL, scope TEXT NOT NULL,
 canonical_event_sha256 TEXT NOT NULL, canonical_ref TEXT NOT NULL, event_json TEXT NOT NULL,
 UNIQUE(collector_id, raw_payload_sha256, source_event_key, origin, scope)
);
CREATE TABLE IF NOT EXISTS audit_entries (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, entry_id TEXT UNIQUE NOT NULL,
 previous_entry_sha256 TEXT, entry_sha256 TEXT NOT NULL, entry_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS media_collections (
 collection_id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(event_id),
 media_id TEXT NOT NULL, artifact_id TEXT NOT NULL REFERENCES evidence_artifacts(artifact_id),
 collected_at TEXT NOT NULL, UNIQUE(event_id, media_id, artifact_id)
);
CREATE TABLE IF NOT EXISTS analytical_runs (
 run_id TEXT PRIMARY KEY, origin TEXT NOT NULL, scope TEXT NOT NULL,
 input_hashes TEXT NOT NULL, parameter_set_id TEXT NOT NULL,
 model_revisions TEXT NOT NULL, report_ref TEXT NOT NULL, report_hash TEXT NOT NULL
);
"""


class EvidenceRepository:
    def __init__(self, data_dir: Path, parameters: Parameters) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self.store = EvidenceStore(data_dir / "evidence")
        self.parameters = parameters
        self._lock = RLock()
        self._db = sqlite3.connect(data_dir / "metadata.sqlite3", check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA busy_timeout=5000")
        self._db.executescript(DDL)
        self._db.execute(
            "INSERT OR IGNORE INTO parameter_sets VALUES (?,?)",
            (parameters.parameter_set_id, canonical_bytes(parameters).decode("utf-8")),
        )
        for table in (
            "parameter_sets",
            "events",
            "evidence_artifacts",
            "audit_entries",
            "media_collections",
            "analytical_runs",
        ):
            for action in ("UPDATE", "DELETE"):
                self._db.execute(
                    f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{action} "
                    f"BEFORE {action} ON {table} "
                    "BEGIN SELECT RAISE(ABORT, 'immutable evidence'); END"
                )
        self._db.commit()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                yield self._db
                self._db.commit()
            except Exception:
                self._db.rollback()
                raise

    def put_artifact(
        self,
        db: sqlite3.Connection,
        data: bytes,
        kind: str,
        mime: str,
        origin: DataOrigin,
        scope: str,
    ) -> tuple[str, str]:
        digest = self.store.put(data)
        existing = db.execute(
            "SELECT artifact_id FROM evidence_artifacts "
            "WHERE sha256=? AND kind=? AND origin=? AND scope=?",
            (digest, kind, origin.value, scope),
        ).fetchone()
        if existing:
            return existing["artifact_id"], digest
        artifact_id = uuid4().hex
        db.execute(
            "INSERT INTO evidence_artifacts VALUES (?,?,?,?,?,?,?)",
            (artifact_id, digest, kind, mime, len(data), origin.value, scope),
        )
        return artifact_id, digest

    def artifact(self, artifact_id: str, scope: str) -> tuple[bytes, str, str]:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM evidence_artifacts WHERE artifact_id=? AND scope=?",
                (artifact_id, scope),
            ).fetchone()
            if row is None:
                raise KeyError("Unknown artifact")
            return self.store.read(row["sha256"]), row["mime_type"], row["kind"]

    def append_audit(
        self,
        db: sqlite3.Connection,
        *,
        action: str,
        origin: DataOrigin,
        actor_id: str,
        **fields: object,
    ) -> AuditTrailEntry:
        previous = db.execute(
            "SELECT entry_sha256 FROM audit_entries ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        body = {
            "entry_id": uuid4().hex,
            "action": action,
            "timestamp_utc": datetime.now(UTC),
            "actor_id": actor_id,
            "previous_entry_sha256": previous[0] if previous else None,
            "parameter_set_id": self.parameters.parameter_set_id,
            "input_data_origin": origin,
            "verification_status": "NOT_CHECKED",
            **fields,
        }
        provisional = AuditTrailEntry.model_validate({**body, "entry_sha256": "0" * 64})
        digest = sha256(canonical_bytes(provisional.model_dump(exclude={"entry_sha256"})))
        entry = AuditTrailEntry.model_validate({**body, "entry_sha256": digest})
        db.execute(
            "INSERT INTO audit_entries(entry_id,previous_entry_sha256,entry_sha256,entry_json) "
            "VALUES (?,?,?,?)",
            (entry.entry_id, entry.previous_entry_sha256, digest, canonical_bytes(entry).decode()),
        )
        return entry

    def get_event(self, event_id: str, scope: str) -> UnifiedSocialEvent:
        with self._lock:
            row = self._db.execute(
                "SELECT event_json FROM events WHERE event_id=? AND scope=?", (event_id, scope)
            ).fetchone()
            if row is None:
                raise KeyError("Unknown event")
            return UnifiedSocialEvent.model_validate_json(row[0])

    def event_count(self, scope: str) -> int:
        with self._lock:
            return self._db.execute(
                "SELECT COUNT(*) FROM events WHERE scope=?", (scope,)
            ).fetchone()[0]

    def collect_media(
        self, event_id: str, media_id: str, data: bytes, mime: str, scope: str
    ) -> str:
        with self.transaction() as db:
            event = self.get_event(event_id, scope)
            if media_id not in {media.media_id for media in event.media_attachments}:
                raise ValueError("Media must be referenced by the original event")
            artifact_id, digest = self.put_artifact(
                db, data, "MEDIA", mime, event.data_origin, scope
            )
            existing = db.execute(
                "SELECT collection_id FROM media_collections "
                "WHERE event_id=? AND media_id=? AND artifact_id=?",
                (event_id, media_id, artifact_id),
            ).fetchone()
            if existing is None:
                db.execute(
                    "INSERT INTO media_collections VALUES (?,?,?,?,?)",
                    (
                        uuid4().hex,
                        event_id,
                        media_id,
                        artifact_id,
                        datetime.now(UTC).isoformat(),
                    ),
                )
                self.append_audit(
                    db,
                    action="MEDIA_COLLECTED",
                    origin=event.data_origin,
                    actor_id="local-collector",
                    event_id=event_id,
                    media_sha256=[digest],
                )
            return artifact_id

    def record_analysis(
        self,
        report: object,
        input_hashes: list[str],
        model_revisions: dict[str, str],
        origin: DataOrigin,
        scope: str,
    ) -> str:
        from app.schemas.models import AnalyticalReport

        if (
            not isinstance(report, AnalyticalReport)
            or report.parameter_set_id != self.parameters.parameter_set_id
        ):
            raise ValueError("Analysis must carry this repository's parameter set")
        with self.transaction() as db:
            for digest in input_hashes:
                if (
                    db.execute(
                        "SELECT 1 FROM evidence_artifacts WHERE sha256=? AND origin=? AND scope=?",
                        (digest, origin.value, scope),
                    ).fetchone()
                    is None
                ):
                    raise ValueError(
                        "Analysis inputs must be retained in the same origin and scope"
                    )
                self.store.read(digest)
            artifact_id, digest = self.put_artifact(
                db, canonical_bytes(report), "ANALYSIS", "application/json", origin, scope
            )
            run_id = uuid4().hex
            db.execute(
                "INSERT INTO analytical_runs VALUES (?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    origin.value,
                    scope,
                    json.dumps(input_hashes),
                    self.parameters.parameter_set_id,
                    json.dumps(model_revisions, sort_keys=True),
                    artifact_id,
                    digest,
                ),
            )
            self.append_audit(
                db, action="ANALYZE", origin=origin, actor_id="pipeline", artifact_sha256=[digest]
            )
            return run_id

    def verify(self, scope: str) -> dict[str, int]:
        with self.transaction() as db:
            for row in db.execute("SELECT * FROM parameter_sets"):
                if sha256(row["parameter_json"].encode("utf-8")) != row["parameter_set_id"]:
                    raise IntegrityMismatch("Parameter set metadata differs from its hash")
            artifacts = db.execute(
                "SELECT * FROM evidence_artifacts WHERE scope=?", (scope,)
            ).fetchall()
            for row in artifacts:
                self.store.read(row["sha256"])
            events = db.execute("SELECT * FROM events WHERE scope=?", (scope,)).fetchall()
            for row in events:
                event = UnifiedSocialEvent.model_validate_json(row["event_json"])
                serialized = canonical_bytes(event.model_dump(exclude={"canonical_event_sha256"}))
                if sha256(serialized) != event.canonical_event_sha256:
                    raise IntegrityMismatch("Canonical event no longer matches its model")
                retained, _, _ = self.artifact(row["canonical_ref"], scope)
                if (
                    retained != serialized
                    or row["canonical_event_sha256"] != event.canonical_event_sha256
                ):
                    raise IntegrityMismatch("Canonical serialization differs from retained event")
                raw, _, _ = self.artifact(event.raw_payload_ref, scope)
                manifest_data, _, _ = self.artifact(event.raw_capture_manifest_ref, scope)
                from app.ingestion.contracts import CaptureManifest

                manifest = CaptureManifest.model_validate_json(manifest_data)
                if (
                    sha256(raw) != event.raw_payload_sha256
                    or manifest.raw_payload_sha256 != event.raw_payload_sha256
                ):
                    raise IntegrityMismatch("Raw capture linkage differs")
            previous = None
            audits = db.execute("SELECT * FROM audit_entries ORDER BY sequence").fetchall()
            for sequence, row in enumerate(audits, start=1):
                entry = AuditTrailEntry.model_validate_json(row["entry_json"])
                digest = sha256(canonical_bytes(entry.model_dump(exclude={"entry_sha256"})))
                if (
                    row["sequence"] != sequence
                    or entry.previous_entry_sha256 != previous
                    or row["previous_entry_sha256"] != previous
                    or entry.entry_sha256 != digest
                    or row["entry_sha256"] != digest
                ):
                    raise IntegrityMismatch("Audit hash chain differs")
                previous = digest
            return {
                "artifacts": len(artifacts),
                "events": len(events),
                "audit_entries": len(audits),
            }
