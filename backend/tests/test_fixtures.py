from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path

import h3
import pytest
from PIL import Image

from app.evidence.canonical import canonical_bytes, sha256
from app.ingestion.service import IngestionService
from app.ingestion.simulator import (
    SCENARIO_IDS,
    fixture_root,
    ingest_scenario,
    load_claim_references,
    load_coverage,
    load_history,
    load_scenario,
    media_bytes,
)
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import DataOrigin, LocationConfidence


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_replay_is_deterministic_and_contains_only_source_contracts(scenario_id: str) -> None:
    sources = load_scenario(scenario_id)
    assert canonical_bytes(sources) == canonical_bytes(load_scenario(scenario_id, seed=42))
    assert canonical_bytes(sources) != canonical_bytes(load_scenario(scenario_id, seed=43))
    assert list(sources) == sorted(
        sources, key=lambda event: (event.timestamp_utc, event.source_event_key)
    )
    assert all(event.data_origin == DataOrigin.SYNTHETIC_REPLAY for event in sources)
    assert len({event.collector_scope for event in sources}) == 1
    encoded = canonical_bytes(sources).decode()
    for forbidden in (
        "bot_indicator_score",
        "cti_score",
        "ground_truth",
        '"role"',
        "heatmap_regions",
    ):
        assert forbidden not in encoded


@pytest.mark.parametrize("scenario_id,authors", [(SCENARIO_IDS[0], 36), (SCENARIO_IDS[1], 15)])
def test_repeated_waves_and_missing_metadata(scenario_id: str, authors: int) -> None:
    sources = load_scenario(scenario_id)
    profiles = {event.account.account_id: event.account for event in sources}
    assert len(profiles) == authors
    assert (
        abs(sum(profile.created_at is None for profile in profiles.values()) / authors - 0.25)
        < 0.06
    )
    assert (
        abs(sum(profile.profile_location is None for profile in profiles.values()) / authors - 0.25)
        < 0.06
    )
    events_by_author = defaultdict(list)
    for event in sources:
        events_by_author[event.account.account_id].append(event)
    repeated = [events for events in events_by_author.values() if len(events) >= 3]
    assert len(repeated) >= (19 if scenario_id == SCENARIO_IDS[0] else 15)
    assert all(
        (events[-1].timestamp_utc - events[0].timestamp_utc).total_seconds() >= 180
        for events in repeated
    )


def test_organic_posts_are_spaced_and_geo_has_observed_external_sources() -> None:
    organic = load_scenario(SCENARIO_IDS[2])
    assert len(organic) == 75
    assert set(Counter(event.account.account_id for event in organic).values()) == {3}
    assert all(
        (b.timestamp_utc - a.timestamp_utc).total_seconds() > 60
        for a, b in zip(organic, organic[1:], strict=False)
    )
    geo = load_scenario(SCENARIO_IDS[1])
    known = [
        event
        for event in geo
        if event.geospatial.source_location_confidence != LocationConfidence.UNAVAILABLE
    ]
    target = geo[0].geospatial.target_h3_index
    assert target is not None
    outside = [
        event for event in known if event.geospatial.source_h3_index not in h3.grid_disk(target, 2)
    ]
    assert 0.7 <= len(outside) / len(known) <= 0.9
    assert len({event.account.account_id for event in known}) >= 5


def test_real_media_and_separate_test_only_masks() -> None:
    baseline = media_bytes("baseline")
    spliced = media_bytes("spliced")
    assert baseline != spliced
    for data in (baseline, spliced):
        with Image.open(BytesIO(data)) as image:
            assert image.format == "JPEG"
            assert image.size == (640, 400)
            image.verify()
    mask_path = fixture_root() / "evaluation" / "spliced-mask.png"
    with Image.open(mask_path) as mask:
        assert mask.size == (640, 400)
        assert mask.getextrema() == (0, 255)
    with pytest.raises(ValueError):
        media_bytes("../evaluation/spliced-mask.png")


def test_fixture_ingestion_retains_media_resolves_parents_and_is_idempotent(
    repository: EvidenceRepository,
) -> None:
    service = IngestionService(repository)
    events = ingest_scenario(SCENARIO_IDS[0], service, scope="test")
    assert len(events) == len(load_scenario(SCENARIO_IDS[0]))
    assert ingest_scenario(SCENARIO_IDS[0], service, scope="test") == events
    ids = {event.event_id for event in events}
    assert all(event.parent_event_id in ids for event in events if event.parent_event_id)
    for event in events:
        for attachment in event.media_attachments:
            assert attachment.evidence_ref is not None
            data, mime, kind = repository.artifact(attachment.evidence_ref, "test")
            assert mime == "image/jpeg" and kind == "MEDIA"
            assert sha256(data) == attachment.sha256_hash
    assert repository.verify("test")["events"] == len(events)


def test_baseline_counts_are_derived_from_raw_events_and_scope_is_exact() -> None:
    history = load_history()
    coverage = load_coverage()
    current = load_scenario(SCENARIO_IDS[1])
    assert len(coverage) >= 168
    assert any(
        not any(
            event.timestamp_utc.replace(minute=0, second=0) == bucket.hour_utc for event in history
        )
        for bucket in coverage
    )
    assert all(bucket.collection_coverage >= 0.9 for bucket in coverage)
    assert all(bucket.collector_scope == current[0].collector_scope for bucket in coverage)
    assert all(event.collector_scope == current[0].collector_scope for event in history)
    assert all(event.timestamp_utc < current[0].timestamp_utc for event in history)
    assert all("count" not in type(bucket).model_fields for bucket in coverage)


def test_claim_registry_snapshots_are_exact_and_synthetic() -> None:
    for reference in load_claim_references():
        assert reference.synthetic_reference
        assert reference.source_url is None
        snapshot = (fixture_root() / reference.snapshot_ref).read_bytes()
        assert sha256(snapshot) == reference.snapshot_sha256
        assert reference.source_title.startswith("Synthetic demo advisory")


def test_training_corpus_is_not_replay_text() -> None:
    corpus = (fixture_root() / "registries" / "training_corpus.txt").read_text(encoding="utf-8")
    assert len(corpus.splitlines()) >= 30
    for scenario_id in SCENARIO_IDS:
        assert all(event.text not in corpus for event in load_scenario(scenario_id))
    for path in (fixture_root() / "raw").glob("*.jsonl"):
        assert Path(path).stat().st_size > 0
