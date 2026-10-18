from pathlib import Path

import pytest

from app.config import Parameters
from app.evidence.store import IntegrityMismatch
from app.ingestion.contracts import SourceEvent
from app.ingestion.service import IngestionService
from app.nlp_engine.engine import NarrativeEngine
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import AccountSyncAssessment, ComputationMode


@pytest.mark.parametrize("damage", ["metadata", "missing_manifest", "malformed_inputs"])
def test_analysis_metadata_is_bound_to_audited_manifest(
    repository: EvidenceRepository, source: SourceEvent, damage: str
) -> None:
    event = IngestionService(repository).ingest(source, scope="test")
    report = AccountSyncAssessment(
        computation_mode="COMPUTED_PIPELINE",
        analysis_status="INSUFFICIENT_DATA",
        parameter_set_id=Parameters().parameter_set_id,
        coverage_ratio=0,
        evidence_reasons=["No history"],
        matched_peer_count=0,
        repeated_bucket_count=0,
    )
    run = repository.record_analysis(
        report, [event.canonical_event_sha256], {"model": "frozen-v1"}, source.data_origin, "test"
    )
    repository.verify("test")
    with repository.transaction() as db:
        if damage == "metadata":
            db.execute("DROP TRIGGER immutable_analytical_runs_UPDATE")
            db.execute(
                "UPDATE analytical_runs SET model_revisions=? WHERE run_id=?",
                ('{"model":"tampered"}', run),
            )
        elif damage == "malformed_inputs":
            db.execute("DROP TRIGGER immutable_analytical_runs_UPDATE")
            db.execute("UPDATE analytical_runs SET input_hashes='42' WHERE run_id=?", (run,))
        else:
            db.execute("DROP TRIGGER immutable_analytical_run_manifests_DELETE")
            db.execute("DELETE FROM analytical_run_manifests WHERE run_id=?", (run,))
    with pytest.raises(IntegrityMismatch, match="manifest|metadata"):
        repository.verify("test")


def test_unavailable_cached_embedder_does_not_block_fallback(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    engine = NarrativeEngine(Parameters(), cached_model=cache)
    assert engine.mode == ComputationMode.HEURISTIC_INDICATOR
    assert engine.embed(["Lucknow election voting"]).any()
    assert any("unavailable" in reason.lower() for reason in engine.limitations)


def test_late_media_enrichment_is_scored_without_mutating_event(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    from app.ingestion.simulator import media_bytes
    from app.pipeline import Pipeline
    from app.repositories.state import StatePartition, StateRepository
    from app.schemas.models import MediaAttachment

    state = StateRepository(repository, "test")
    pipeline = Pipeline(state)
    partition = StatePartition(
        data_origin=source.data_origin, collector_scope=source.collector_scope
    )
    pending = source.model_copy(
        update={
            "media_attachments": (
                MediaAttachment(media_id="late", media_type="image", collection_status="PENDING"),
            )
        }
    )
    event = pipeline.activate(pending, partition, 0)
    original = event.model_dump_json()
    before, _ = pipeline.refresh(partition, 0)
    assert (
        not before[0].media_reports and before[0].cti_assessment.media_forensics_component is None
    )
    repository.collect_media(event.event_id, "late", media_bytes("baseline"), "image/jpeg", "test")
    after, _ = pipeline.refresh(partition, 0)
    assert after[0].media_reports[0].analysis_status.value == "AVAILABLE"
    assert repository.get_event(event.event_id, "test").model_dump_json() == original
    assert after[0].sample_posts[0].media_attachments[0].collection_status == "PENDING"
    repository.verify("test")


def test_review_arriving_during_recalculation_is_preserved(
    repository: EvidenceRepository, source: SourceEvent, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.ingestion.simulator import CLAIMS
    from app.nlp_engine.review import review_claim
    from app.pipeline import Pipeline
    from app.repositories.state import StatePartition, StateRepository
    from app.schemas.models import ClaimReviewRequest, DataOrigin, GeospatialContext

    state = StateRepository(repository, "test")
    pipeline = Pipeline(state)
    observed = source.model_copy(
        update={
            "text": CLAIMS[0],
            "language": "en",
            "data_origin": DataOrigin.SYNTHETIC_REPLAY,
            "geospatial": GeospatialContext(target_region_name="Lucknow"),
        }
    )
    partition = StatePartition(
        data_origin=observed.data_origin, collector_scope=observed.collector_scope
    )
    pipeline.activate(observed, partition, 0)
    initial = pipeline.refresh(partition, 0)[0][0]
    original = state.list_claim_reviews
    called = False

    def interleaved(campaign_id: str) -> list:
        nonlocal called
        if not called:
            called = True
            candidate = initial.claim_verification.candidate_reference
            assert candidate is not None
            assessment = review_claim(
                state,
                initial,
                ClaimReviewRequest(
                    reference_id=candidate.reference_id,
                    status="CONTEXT_MISSING",
                    analyst_note="Date and region match; media context remains missing.",
                ),
                "local-analyst:test",
            )
            updated = initial.model_copy(
                update={"claim_verification": assessment, "snapshot_revision": 2}
            )
            repository.record_analysis(
                updated,
                [event.canonical_event_sha256 for event in initial.sample_posts],
                {"review": "human-context-v1"},
                initial.data_origin,
                "test",
            )
            state.put_campaign(partition, 0, updated)
            return []
        return original(campaign_id)

    monkeypatch.setattr(state, "list_claim_reviews", interleaved)
    final = pipeline.refresh(partition, 0)[0][0]
    assert final.snapshot_revision == 3
    assert final.claim_verification.status.value == "CONTEXT_MISSING"
