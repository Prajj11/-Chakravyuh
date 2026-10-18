import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Parameters
from app.evidence.canonical import canonical_bytes, sha256
from app.evidence.store import EvidenceStore, IntegrityMismatch
from app.ingestion.contracts import CaptureManifest, SourceEvent
from app.ingestion.service import IngestionService
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import (
    AccountSyncAssessment,
    DataOrigin,
    MediaAttachment,
)


def test_canonical_golden_vector() -> None:
    value = {
        "z": [None, True, 1.5],
        "text": "नमस्ते  e\u0301",
        "at": datetime(2026, 10, 18, 5, 30, tzinfo=timezone(timedelta(hours=5, minutes=30))),
    }
    expected = (
        '{"at":"2026-10-18T00:00:00.000000Z","text":"नमस्ते  e\u0301","z":[null,true,1.5]}'.encode()
    )
    assert canonical_bytes(value) == expected
    assert canonical_bytes(dict(reversed(list(value.items())))) == expected
    assert canonical_bytes(["a", "b"]) != canonical_bytes(["b", "a"])


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), datetime(2026, 10, 18)])
def test_canonical_rejects_invalid_values(bad: object) -> None:
    with pytest.raises(ValueError):
        canonical_bytes({"invalid": bad})


def test_ingestion_preserves_bytes_and_is_idempotent(
    repository: EvidenceRepository,
    source: SourceEvent,
) -> None:
    source = SourceEvent.model_validate({**source.model_dump(), "data_origin": "PUBLIC_OSINT"})
    raw = b' { "text": "original source entity", "posts": [1, 2] }\n'
    service = IngestionService(repository)
    event = service.ingest(source, scope="local", raw_bytes=raw, source_pointer="/posts/0")
    duplicate = service.ingest(source, scope="local", raw_bytes=raw, source_pointer="/posts/0")
    assert duplicate == event
    assert repository.artifact(event.raw_payload_ref, "local")[0] == raw
    assert event.raw_payload_sha256 == sha256(raw)
    assert event.raw_payload_sha256 != event.canonical_event_sha256
    manifest = CaptureManifest.model_validate_json(
        repository.artifact(event.raw_capture_manifest_ref, "local")[0]
    )
    assert manifest.source_pointer == "/posts/0"
    assert manifest.collection_timestamp_utc > datetime(2026, 1, 1, tzinfo=UTC)
    assert event.text == source.text
    assert repository.verify("local") == {"artifacts": 3, "events": 1, "audit_entries": 1}


def test_deep_event_immutability(repository: EvidenceRepository, source: SourceEvent) -> None:
    event = IngestionService(repository).ingest(source, scope="local")
    with pytest.raises(ValidationError):
        event.account.handle = "changed"
    with pytest.raises(TypeError):
        event.hashtags[0] = "changed"
    copy = event.model_dump()
    copy["account"]["handle"] = "outside-copy"
    assert repository.get_event(event.event_id, "local").account.handle == "@author"


def test_scope_and_origin_are_isolated(repository: EvidenceRepository, source: SourceEvent) -> None:
    service = IngestionService(repository)
    a = service.ingest(source, scope="one")
    b = service.ingest(source, scope="two")
    synthetic = SourceEvent.model_validate(
        {**source.model_dump(), "data_origin": "SYNTHETIC_REPLAY"}
    )
    c = service.ingest(synthetic, scope="one")
    assert len({a.event_id, b.event_id, c.event_id}) == 3
    with pytest.raises(KeyError):
        repository.artifact(a.raw_payload_ref, "two")
    with pytest.raises(KeyError):
        repository.get_event(a.event_id, "two")
    assert repository.verify("one")["events"] == 2


def test_concurrent_ingestion_serializes_audit(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    service = IngestionService(repository)

    def ingest(index: int) -> str:
        item = SourceEvent.model_validate(
            {**source.model_dump(), "source_event_key": f"post-{index}"}
        )
        return service.ingest(item, scope="local").event_id

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(ingest, [0, 1, 2, 3, 0, 1, 2, 3]))
    assert len(set(ids)) == 4
    assert repository.verify("local")["audit_entries"] == 4


def test_late_media_is_append_only(repository: EvidenceRepository, source: SourceEvent) -> None:
    source = SourceEvent.model_validate(
        {
            **source.model_dump(),
            "media_attachments": [
                MediaAttachment(media_id="later", media_type="image", collection_status="PENDING")
            ],
        }
    )
    event = IngestionService(repository).ingest(source, scope="local")
    artifact = repository.collect_media(
        event.event_id, "later", b"exact media", "image/jpeg", "local"
    )
    assert (
        repository.collect_media(event.event_id, "later", b"exact media", "image/jpeg", "local")
        == artifact
    )
    assert repository.get_event(event.event_id, "local") == event
    assert repository.artifact(artifact, "local")[0] == b"exact media"
    assert repository.verify("local")["audit_entries"] == 2


@pytest.mark.parametrize(
    "kind", ["RAW_PAYLOAD", "CANONICAL_EVENT", "CAPTURE_MANIFEST", "MEDIA", "ANALYSIS"]
)
def test_byte_corruption_is_detected(
    repository: EvidenceRepository,
    source: SourceEvent,
    kind: str,
) -> None:
    IngestionService(repository).ingest(source, scope="local")
    with repository.transaction() as db:
        if kind in {"MEDIA", "ANALYSIS"}:
            repository.put_artifact(
                db, b"original", kind, "application/octet-stream", source.data_origin, "local"
            )
        row = db.execute("SELECT sha256 FROM evidence_artifacts WHERE kind=?", (kind,)).fetchone()
    repository.store._path(row[0]).write_bytes(b"corrupted")
    with pytest.raises(IntegrityMismatch):
        repository.verify("local")


def test_audit_corruption_is_detected(repository: EvidenceRepository, source: SourceEvent) -> None:
    IngestionService(repository).ingest(source, scope="local")
    # Emulate privileged corruption which bypasses application append-only triggers.
    with repository.transaction() as db:
        db.execute("DROP TRIGGER immutable_audit_entries_UPDATE")
        db.execute("UPDATE audit_entries SET entry_sha256=?", ("f" * 64,))
    with pytest.raises(IntegrityMismatch):
        repository.verify("local")


@pytest.mark.parametrize(
    "table", ["events", "audit_entries", "evidence_artifacts", "parameter_sets"]
)
def test_repository_blocks_sql_mutation(
    repository: EvidenceRepository, source: SourceEvent, table: str
) -> None:
    IngestionService(repository).ingest(source, scope="local")
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        with repository.transaction() as db:
            db.execute(f"DELETE FROM {table}")


def test_existing_corrupt_blob_is_never_overwritten(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path)
    digest = store.put(b"original")
    store._path(digest).write_bytes(b"tampered")
    with pytest.raises(IntegrityMismatch):
        store.put(b"original")
    assert store._path(digest).read_bytes() == b"tampered"
    with pytest.raises(ValueError):
        store.read("../outside")


def test_analysis_lineage_rejects_cross_origin(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    event = IngestionService(repository).ingest(source, scope="local")
    report = AccountSyncAssessment(
        computation_mode="COMPUTED_PIPELINE",
        analysis_status="INSUFFICIENT_DATA",
        parameter_set_id=Parameters().parameter_set_id,
        coverage_ratio=0,
        evidence_reasons=["Insufficient observation span"],
        missing_signals=["history"],
        matched_peer_count=0,
        repeated_bucket_count=0,
    )
    with pytest.raises(ValueError, match="same origin"):
        repository.record_analysis(
            report, [event.raw_payload_sha256], {}, DataOrigin.SYNTHETIC_REPLAY, "local"
        )
    repository.record_analysis(report, [event.raw_payload_sha256], {}, source.data_origin, "local")
    assert repository.verify("local")["audit_entries"] == 2


def test_evidence_survives_restart(tmp_path: Path, source: SourceEvent) -> None:
    first = EvidenceRepository(tmp_path, Parameters())
    event = IngestionService(first).ingest(source, scope="local")
    first.close()
    second = EvidenceRepository(tmp_path, Parameters())
    try:
        assert second.get_event(event.event_id, "local") == event
        assert second.verify("local")["events"] == 1
    finally:
        second.close()
