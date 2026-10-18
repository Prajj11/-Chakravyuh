"""Deterministic source observations; evaluation labels never enter this module."""

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import h3
from pydantic import Field

from app.evidence.canonical import sha256
from app.ingestion.contracts import SourceEvent
from app.ingestion.service import IngestionService
from app.schemas.models import (
    AccountProfile,
    ClaimReference,
    ContractModel,
    DataOrigin,
    GeospatialContext,
    InteractionType,
    LocationConfidence,
    MediaAttachment,
    PlatformType,
    UnifiedSocialEvent,
    UTCDateTime,
)

SCENARIO_IDS = ("cmp_electoral_01", "cmp_geo_astroturf_02", "cmp_organic_03")
START = datetime(2026, 10, 1, 12, tzinfo=UTC)
CLAIMS = (
    "Lucknow election voting machines changed the votes. Block the polling station now.",
    "Lucknow relief supplies are poisoned. Panic now and stop all deliveries.",
)


class CoverageHour(ContractModel):
    collector_scope: str
    topic_family_id: str = "civic-participation"
    h3_index: str
    hour_utc: UTCDateTime
    collection_coverage: float = Field(ge=0, le=1)


def fixture_root() -> Path:
    return Path(__file__).resolve().parents[3] / "sample_data"


def media_bytes(media_id: str) -> bytes:
    if media_id not in {"baseline", "spliced"}:
        raise ValueError("Unknown fixture media")
    return (fixture_root() / "media" / f"{media_id}.jpg").read_bytes()


def replay_scope(scenario_id: str, seed: int = 42) -> str:
    return f"replay-v1:{scenario_id}:seed-{seed}"


def load_scenario(scenario_id: str, seed: int = 42) -> tuple[SourceEvent, ...]:
    from app.ingestion.case_catalogue import CASE_BY_ID
    from app.ingestion.case_pack import generate_case

    if scenario_id in CASE_BY_ID:
        return generate_case(scenario_id, seed)
    if scenario_id not in SCENARIO_IDS:
        raise ValueError("Unknown replay scenario")
    rng = random.Random(seed)
    organic = scenario_id == SCENARIO_IDS[2]
    geo = scenario_id == SCENARIO_IDS[1]
    authors = 25 if organic else 15 if geo else 36
    missing = set(rng.sample(range(authors), round(authors / 4)))
    known_authors = [author for author in range(authors) if author not in missing]
    external_authors = set(known_authors[: round(len(known_authors) * 0.8)])
    target = h3.latlng_to_cell(26.8467, 80.9462, 5)
    external = [
        (28.6139, 77.2090, "Delhi"),
        (19.076, 72.8777, "Mumbai"),
        (12.9716, 77.5946, "Bengaluru"),
        (22.5726, 88.3639, "Kolkata"),
    ]
    sources = []
    for author in range(authors):
        actor = f"{scenario_id}-{seed}-{author:06d}"
        profile = AccountProfile(
            account_id="simulator:" + actor,
            handle=f"@{'participant' if organic else 'relay'}_{seed}_{author:06d}",
            created_at=None
            if author in missing
            else START - timedelta(days=400 if organic else 20, hours=author % 3),
            profile_location=None if author in missing else "Lucknow",
        )
        for wave in range(3):
            if organic:
                subject = ("gardens", "schools", "transport", "libraries", "markets")[author % 5]
                seconds = (wave * authors + author) * 79 + rng.randint(0, 5)
                text = (
                    f"Neighbourhood discussion {seed}: participant {author} shares observation "
                    f"{wave} about {subject}. "
                    f"Personal note {actor}/{wave}; please check the local details."
                )
            else:
                seconds = wave * 120 + (
                    0 if author == 0 else rng.randint(4, 18) if author < 19 else 35 + author * 8
                )
                text = CLAIMS[1 if geo else 0]
                if author >= 21:
                    text += (
                        f" My observation from neighbourhood {author}; please investigate context."
                    )
            if author % 3 == 1:
                text += " यह एक अवलोकन है; संदर्भ की जाँच करें।"
            elif author % 3 == 2:
                text += " Yeh ek observation hai; sandarbh ki jaanch karein."
            known = author not in missing
            lat, lon, region = (26.8467, 80.9462, "Lucknow")
            if geo and author in external_authors:
                lat, lon, region = external[author % len(external)]
            source_geo = GeospatialContext(
                source_lat=lat if known else None,
                source_lon=lon if known else None,
                source_h3_index=h3.latlng_to_cell(lat, lon, 5) if known else None,
                source_region_name=region if known else None,
                source_location_confidence=LocationConfidence.EXPLICIT_GPS
                if known
                else LocationConfidence.UNAVAILABLE,
                target_region_name="Lucknow",
                target_h3_index=target,
            )
            sources.append(
                SourceEvent(
                    source_event_key=f"{actor}-wave-{wave}",
                    platform=PlatformType.SIMULATOR,
                    data_origin=DataOrigin.SYNTHETIC_REPLAY,
                    collector_id="seeded-replay-v1",
                    collector_scope=replay_scope(scenario_id, seed),
                    timestamp_utc=START + timedelta(seconds=seconds),
                    account=profile,
                    text=text,
                    language=("en", "hi", "hinglish")[author % 3],
                    urls=() if organic else ("https://example.invalid/demo-observation",),
                    media_attachments=(
                        MediaAttachment(
                            media_id="baseline" if organic else "spliced",
                            media_type="image",
                            collection_status="PENDING",
                        ),
                    ),
                    interaction_type=InteractionType.ORIGINAL_POST
                    if organic or author == 0
                    else InteractionType.REPOST,
                    parent_event_id=None
                    if organic or author == 0
                    else f"source:{scenario_id}-{seed}-000000-wave-{wave}",
                    geospatial=source_geo,
                )
            )
    return tuple(sorted(sources, key=lambda event: (event.timestamp_utc, event.source_event_key)))


def retain_source(
    source: SourceEvent, service: IngestionService, *, scope: str, parent_ids: dict[str, str]
) -> UnifiedSocialEvent:
    retained = []
    for media in source.media_attachments:
        data = media_bytes(media.media_id)
        with service.repository.transaction() as db:
            artifact_id, digest = service.repository.put_artifact(
                db, data, "MEDIA", "image/jpeg", source.data_origin, scope
            )
        retained.append(
            MediaAttachment(
                media_id=media.media_id,
                media_type="image",
                collection_status="COLLECTED",
                sha256_hash=digest,
                evidence_ref=artifact_id,
            )
        )
    parent = source.parent_event_id
    if parent and parent.startswith("source:"):
        parent = parent_ids.get(parent[7:])
        if parent is None:
            raise ValueError("Replay parent must precede its child")
    normalized = SourceEvent.model_validate(
        {**source.model_dump(), "media_attachments": tuple(retained), "parent_event_id": parent}
    )
    event = service.ingest(normalized, scope=scope)
    parent_ids[source.source_event_key] = event.event_id
    return event


def ingest_scenario(
    scenario_id: str, service: IngestionService, *, scope: str, seed: int = 42
) -> tuple[UnifiedSocialEvent, ...]:
    parents: dict[str, str] = {}
    return tuple(
        retain_source(source, service, scope=scope, parent_ids=parents)
        for source in load_scenario(scenario_id, seed)
    )


def load_coverage(seed: int = 42) -> tuple[CoverageHour, ...]:
    return tuple(
        CoverageHour(
            collector_scope=replay_scope(SCENARIO_IDS[1], seed),
            h3_index=h3.latlng_to_cell(26.8467, 80.9462, 5),
            hour_utc=START - timedelta(hours=hour + 2),
            collection_coverage=1,
        )
        for hour in range(240)
    )


def load_history(seed: int = 42) -> tuple[SourceEvent, ...]:
    profile = AccountProfile(
        account_id=f"simulator:historian-{seed}", handle="@historical-observer"
    )
    return tuple(
        SourceEvent(
            source_event_key=f"history-{seed}-{index}-{offset}",
            platform=PlatformType.SIMULATOR,
            data_origin=DataOrigin.SYNTHETIC_REPLAY,
            collector_id="seeded-replay-v1",
            collector_scope=bucket.collector_scope,
            timestamp_utc=bucket.hour_utc + timedelta(minutes=offset * 10),
            account=profile,
            text=f"Lucknow community participation bulletin {index} record {offset}.",
            language="en",
            geospatial=GeospatialContext(
                target_region_name="Lucknow", target_h3_index=bucket.h3_index
            ),
        )
        for index, bucket in enumerate(load_coverage(seed))
        for offset in range(index % 4)
    )


def load_claim_references() -> tuple[ClaimReference, ...]:
    path = fixture_root() / "registries" / "known_claims_registry.json"
    references = tuple(
        ClaimReference.model_validate(value)
        for value in json.loads(path.read_text(encoding="utf-8"))
    )
    for reference in references:
        path = (fixture_root() / reference.snapshot_ref).resolve()
        if (
            not path.is_relative_to(fixture_root().resolve())
            or sha256(path.read_bytes()) != reference.snapshot_sha256
        ):
            raise ValueError("Claim reference snapshot integrity failed")
    return references
