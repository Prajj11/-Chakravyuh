"""One capture/normalization service for replay, injection and future public adapters."""

from datetime import UTC, datetime
from typing import Literal

from app.evidence.canonical import canonical_bytes, sha256
from app.ingestion.contracts import CaptureManifest, SourceEvent
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import UnifiedSocialEvent


class IngestionService:
    def __init__(self, repository: EvidenceRepository) -> None:
        self.repository = repository

    def ingest(
        self,
        source: SourceEvent,
        *,
        scope: str,
        raw_bytes: bytes | None = None,
        content_type: str = "application/json",
        source_pointer: str | None = None,
    ) -> UnifiedSocialEvent:
        if (source.data_origin.value == "PUBLIC_OSINT") != (raw_bytes is not None):
            raise ValueError(
                "Public sources require original bytes; replay/injection use source objects"
            )
        capture_format: Literal["HTTP_ENTITY_BYTES", "CANONICAL_JSON_V1"] = (
            "HTTP_ENTITY_BYTES" if raw_bytes is not None else "CANONICAL_JSON_V1"
        )
        raw = raw_bytes if raw_bytes is not None else canonical_bytes(source)
        raw_hash = sha256(raw)
        repo = self.repository
        with repo.transaction() as db:
            existing = db.execute(
                "SELECT event_json FROM events WHERE collector_id=? AND raw_payload_sha256=? "
                "AND source_event_key=? AND origin=? AND scope=?",
                (
                    source.collector_id,
                    raw_hash,
                    source.source_event_key,
                    source.data_origin.value,
                    scope,
                ),
            ).fetchone()
            if existing:
                return UnifiedSocialEvent.model_validate_json(existing[0])
            collection_time = datetime.now(UTC)
            raw_ref, _ = repo.put_artifact(
                db, raw, "RAW_PAYLOAD", content_type, source.data_origin, scope
            )
            manifest = CaptureManifest(
                collector_id=source.collector_id,
                collector_scope=source.collector_scope,
                source_event_key=source.source_event_key,
                source_url=source.source_url,
                content_type=content_type,
                capture_format=capture_format,
                collection_timestamp_utc=collection_time,
                raw_payload_sha256=raw_hash,
                raw_payload_ref=raw_ref,
                data_origin=source.data_origin,
                source_pointer=source_pointer,
            )
            manifest_ref, _ = repo.put_artifact(
                db,
                canonical_bytes(manifest),
                "CAPTURE_MANIFEST",
                "application/json",
                source.data_origin,
                scope,
            )
            identity = canonical_bytes(
                [
                    source.collector_id,
                    source.source_event_key,
                    raw_hash,
                    source.data_origin.value,
                    scope,
                ]
            )
            body = source.model_dump(exclude={"source_event_key", "collector_scope"})
            body.update(
                event_id=sha256(identity),
                collection_timestamp_utc=collection_time,
                raw_payload_sha256=raw_hash,
                raw_payload_ref=raw_ref,
                raw_capture_manifest_ref=manifest_ref,
                raw_capture_format=capture_format,
                canonical_event_sha256="0" * 64,
            )
            provisional = UnifiedSocialEvent.model_validate(body)
            event_bytes = canonical_bytes(
                provisional.model_dump(exclude={"canonical_event_sha256"})
            )
            body["canonical_event_sha256"] = sha256(event_bytes)
            event = UnifiedSocialEvent.model_validate(body)
            # Collected attachments must be registered here. No URL fetches occur here.
            for media in event.media_attachments:
                if media.evidence_ref is not None:
                    media_bytes, _, kind = repo.artifact(media.evidence_ref, scope)
                    row = db.execute(
                        "SELECT origin FROM evidence_artifacts WHERE artifact_id=?",
                        (media.evidence_ref,),
                    ).fetchone()
                    if (
                        kind != "MEDIA"
                        or sha256(media_bytes) != media.sha256_hash
                        or row[0] != source.data_origin.value
                    ):
                        raise ValueError("Media evidence must match retained bytes and origin")
            canonical_ref, _ = repo.put_artifact(
                db, event_bytes, "CANONICAL_EVENT", "application/json", source.data_origin, scope
            )
            db.execute(
                "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    event.event_id,
                    event.collector_id,
                    raw_hash,
                    source.source_event_key,
                    source.data_origin.value,
                    scope,
                    event.canonical_event_sha256,
                    canonical_ref,
                    canonical_bytes(event).decode("utf-8"),
                ),
            )
            repo.append_audit(
                db,
                action="INGEST",
                origin=event.data_origin,
                actor_id="local-collector",
                event_id=event.event_id,
                collector_id=event.collector_id,
                collection_timestamp_utc=collection_time,
                raw_payload_sha256=raw_hash,
                canonical_event_sha256=event.canonical_event_sha256,
                media_sha256=[
                    item.sha256_hash for item in event.media_attachments if item.sha256_hash
                ],
            )
            return event
