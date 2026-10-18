from datetime import timedelta

import pytest

from app.config import Parameters
from app.coordination.engine import CoordinationEngine
from app.ingestion.contracts import SourceEvent
from app.ingestion.service import IngestionService
from app.ingestion.simulator import SCENARIO_IDS, ingest_scenario
from app.nlp_engine.engine import NarrativeEngine
from app.reporting.cti import AlertState, compute_cti, threat_level
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import CampaignThreatBreakdown


@pytest.mark.parametrize(
    "score,tier",
    [(39.999, "LOW"), (40, "MEDIUM"), (60, "HIGH"), (75, "CRITICAL"), (100, "CRITICAL")],
)
def test_unrounded_tiers(score: float, tier: str) -> None:
    assert threat_level(score, Parameters()).value == tier


def assessment(score: float = 90) -> CampaignThreatBreakdown:
    return CampaignThreatBreakdown(
        computation_mode="COMPUTED_PIPELINE",
        analysis_status="AVAILABLE",
        parameter_set_id=Parameters().parameter_set_id,
        coverage_ratio=1,
        evidence_reasons=["test"],
        feature_contributions={"sync": score},
        cti_score=score,
        threat_level=threat_level(score, Parameters()),
        sync_component=100,
        component_modes={"sync": "COMPUTED_PIPELINE"},
        effective_weights={"sync": 1},
        scored_post_coverage_ratio=1,
        alert_eligible=score >= 75,
    )


def test_alert_cooldown_rearm_and_late_events(source: SourceEvent) -> None:
    p = Parameters()
    state = AlertState()
    high, low = assessment(), assessment(50)
    start = source.timestamp_utc
    assert state.observe(high, start, p)
    assert not state.observe(high, start + timedelta(seconds=500), p)
    assert not state.observe(low, start + timedelta(seconds=501), p)
    assert not state.observe(high, start + timedelta(seconds=600), p)
    assert not state.observe(low, start + timedelta(seconds=601), p)
    assert not state.observe(low, start + timedelta(seconds=721), p)
    assert state.observe(high, start + timedelta(seconds=722), p)
    assert not state.observe(high, start + timedelta(seconds=1), p)


def test_cti_missing_sync_and_no_media_vs_failed_media(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    p = Parameters()
    event = IngestionService(repository).ingest(source, scope="test")
    sync = CoordinationEngine(p).analyze([event], similarity=lambda _a, _b: 0)
    result = compute_cti(
        p, [event], sync.assessment, sync.bots, [], [], NarrativeEngine(p).harm([event])
    )
    assert result.cti_score is None and result.media_forensics_component == 0
    events = list(ingest_scenario(SCENARIO_IDS[1], IngestionService(repository), scope="test"))
    sync = CoordinationEngine(p).analyze(events, similarity=lambda _a, _b: 1)
    result = compute_cti(
        p, events, sync.assessment, sync.bots, [], [], NarrativeEngine(p).harm(events)
    )
    assert result.media_forensics_component is None
    assert sum(result.effective_weights.values()) == pytest.approx(1)
    assert sum(result.feature_contributions.values()) == pytest.approx(result.cti_score)
