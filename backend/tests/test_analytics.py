import math
from datetime import timedelta

import pytest

from app.config import Parameters
from app.coordination.engine import CoordinationEngine
from app.ingestion.contracts import SourceEvent
from app.ingestion.service import IngestionService
from app.nlp_engine.engine import NarrativeEngine, normalize_text, normalize_url
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import AccountProfile, DataOrigin, UnifiedSocialEvent


def events_for(
    repository: EvidenceRepository,
    source: SourceEvent,
    times: dict[str, list[int]],
    text: str = "Lucknow election voting machines votes",
) -> list[UnifiedSocialEvent]:
    service = IngestionService(repository)
    events = []
    for author, timestamps in times.items():
        for index, seconds in enumerate(timestamps):
            events.append(
                service.ingest(
                    source.model_copy(
                        update={
                            "source_event_key": f"{author}-{index}",
                            "text": text,
                            "language": "en",
                            "account": AccountProfile(
                                account_id=f"simulator:{author}", handle=f"@{author}"
                            ),
                            "timestamp_utc": source.timestamp_utc + timedelta(seconds=seconds),
                        }
                    ),
                    scope="test",
                )
            )
    return events


def test_frozen_vectors_normalization_and_zero_vector() -> None:
    engine = NarrativeEngine(Parameters())
    before = engine.embed(["Lucknow election voting machines"])
    engine.embed(["brand new vocabulary never fit on this input"])
    assert (before == engine.embed(["Lucknow election voting machines"])).all()
    assert normalize_url("https://example.org/p?utm_source=x&a=1#x") == "https://example.org/p?a=1"
    assert normalize_text("  MATDAN   मतदान  ") == "voting voting"
    assert not engine.embed(["𓀀𓀁𓀂"])[0].any()


def test_clustering_window_and_partition_identity(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    engine = NarrativeEngine(Parameters())
    events = events_for(repository, source, {"a": [0, 10, 90000]})
    clusters = engine.cluster(events, partition_id="one")
    assert sum(len(cluster.event_ids) for cluster in clusters) == 1
    assert clusters[0].campaign_id != engine.cluster(events, partition_id="two")[0].campaign_id
    assert events[0].text == "Lucknow election voting machines votes"


@pytest.mark.parametrize("delta,eligible", [(0, True), (60, True), (61, False)])
def test_pair_boundaries_and_repeated_buckets(
    repository: EvidenceRepository, source: SourceEvent, delta: int, eligible: bool
) -> None:
    events = events_for(
        repository, source, {"a": [0, 120, 240], "b": [delta, 120 + delta, 240 + delta]}
    )
    # With 61s the neighbouring wave is 59s away; remove that alternate match.
    if delta == 61:
        events = events_for(
            repository,
            source.model_copy(update={"collector_id": "second"}),
            {"a": [0, 180, 360], "b": [61, 241, 421]},
        )
    result = CoordinationEngine(Parameters()).analyze(events, similarity=lambda _a, _b: 1)
    assert bool(result.edges) == eligible
    if eligible:
        edge = result.edges[0]
        assert len(edge.matches) == 3
        assert edge.weight == pytest.approx(1 - math.exp(-3 * math.exp(-delta / 20)))
        assert sum(result.accounts["simulator:a"].feature_contributions.values()) == pytest.approx(
            edge.weight
        )


def test_single_bucket_and_hashtag_only_never_create_sync(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    engine = CoordinationEngine(Parameters())
    burst = events_for(repository, source, {"a": [0, 1, 2], "b": [0, 1, 2]})
    assert engine.analyze(burst, similarity=lambda _a, _b: 1).edges == []
    spaced = events_for(
        repository,
        source.model_copy(update={"collector_id": "spaced"}),
        {"a": [0, 120, 240], "b": [0, 120, 240]},
    )
    assert engine.analyze(spaced, similarity=lambda _a, _b: 0).edges == []


def test_disjoint_pairing_and_campaign_zero_vs_null(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    engine = CoordinationEngine(Parameters())
    events = events_for(
        repository, source, {"a": [0, 1, 180, 360], "b": [0, 180, 360], "c": [0, 180, 360]}
    )
    result = engine.analyze(events, similarity=lambda _a, _b: 1)
    assert result.assessment.sync_score is not None
    for edge in result.edges:
        matched = [event_id for pair in edge.matches for event_id in (pair.event_a, pair.event_b)]
        assert len(matched) == len(set(matched))
    zero = engine.analyze(events, similarity=lambda _a, _b: 0)
    assert zero.assessment.sync_score == 0
    assert engine.analyze(events[:1], similarity=lambda _a, _b: 0).assessment.sync_score is None


def test_bot_missing_features_and_additive_scaling(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    events = events_for(repository, source, {"a": [0, 180, 360]})
    result = CoordinationEngine(Parameters()).analyze(events, similarity=lambda _a, _b: 0)
    bot = result.bots["simulator:a"]
    assert bot.bot_indicator_score == 0
    assert bot.coverage_ratio == pytest.approx(0.65)
    assert "creation_batch_density" in bot.missing_signals
    assert "posting_rate_burst" in bot.missing_signals
    assert sum(bot.feature_contributions.values()) == bot.bot_indicator_score
    assert (
        CoordinationEngine(Parameters())
        .analyze(events[:1], similarity=lambda _a, _b: 0)
        .bots["simulator:a"]
        .bot_indicator_score
        is None
    )


def test_claim_retrieval_never_verifies_and_is_origin_isolated(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    from app.ingestion.simulator import CLAIMS, load_claim_references

    engine = NarrativeEngine(Parameters())
    candidate = engine.claim(
        CLAIMS[0], DataOrigin.SYNTHETIC_REPLAY, source.timestamp_utc, load_claim_references()
    )
    assert candidate.candidate_reference is not None
    assert candidate.status.value == "UNVERIFIED"
    assert (
        engine.claim(
            CLAIMS[0], DataOrigin.USER_INJECTED, source.timestamp_utc, load_claim_references()
        ).candidate_reference
        is None
    )


def test_harm_supported_zero_and_unavailable(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    engine = NarrativeEngine(Parameters())
    events = events_for(repository, source, {"a": [0]})
    assert engine.harm(events).harm_indicator_score == 0
    assert (
        engine.harm([events[0].model_copy(update={"language": "xx"})]).harm_indicator_score is None
    )
    assert (
        engine.harm([events[0].model_copy(update={"text": "panic now"})]).harm_indicator_score == 85
    )


def test_empty_and_all_missing_are_unavailable(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    engine = CoordinationEngine(Parameters())
    empty = engine.analyze([], similarity=lambda _a, _b: 0)
    assert empty.assessment.sync_score is None
    assert empty.assessment.coverage_ratio == 0
    events = events_for(repository, source, {"a": [0]})
    blank = events[0].model_copy(
        update={"account": AccountProfile(account_id="simulator:a", handle="")}
    )
    bot = engine.analyze([blank], similarity=lambda _a, _b: 0).bots["simulator:a"]
    assert bot.bot_indicator_score is None and bot.coverage_ratio == 0


def test_burst_uses_completed_bins_and_retains_zero_hours(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    engine = CoordinationEngine(Parameters())
    events = events_for(repository, source, {"a": list(range(20)) + [600]})
    assert engine.burst(events) == pytest.approx(20)
    assert engine.burst(events[:-1]) is None
