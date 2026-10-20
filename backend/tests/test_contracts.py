import inspect
from datetime import UTC, datetime

import h3
import pytest
from pydantic import BaseModel, ValidationError

from app.config import Parameters, Settings
from app.schemas import models as m


def test_all_wire_models_generate_schema() -> None:
    for _, cls in inspect.getmembers(m, inspect.isclass):
        if issubclass(cls, BaseModel) and cls.__module__ == m.__name__:
            cls.model_json_schema()
            cls.model_json_schema(mode="serialization")


def test_parameter_hash_is_stable_and_changes_with_defaults() -> None:
    defaults = Parameters()
    assert defaults.parameter_set_id == Parameters().parameter_set_id
    changed = Parameters(SEMANTIC_CLUSTER_SIMILARITY=0.86)
    assert defaults.parameter_set_id != changed.parameter_set_id
    with pytest.raises(ValidationError):
        Parameters(TEMPORAL_DECAY_TAU_SEC=0)
    # Legacy token settings are accepted but no longer control local access.
    Settings(session_token="short")
    with pytest.raises(ValidationError):
        Settings(frontend_origin="*")
    with pytest.raises(ValidationError):
        Settings(frontend_origin="http://outside.example:3000")


def test_utc_and_extra_fields() -> None:
    profile = m.AccountProfile(
        account_id="simulator:one", handle="@one", created_at="2026-10-18T05:30:00+05:30"
    )
    assert profile.model_dump(mode="json")["created_at"] == "2026-10-18T00:00:00.000000Z"
    with pytest.raises(ValidationError):
        m.AccountProfile(account_id="one", handle="@one", invented_score=100)
    with pytest.raises(ValidationError):
        m.AccountProfile(account_id="one", handle="@one", created_at=datetime(2026, 10, 18))


@pytest.mark.parametrize(
    "data",
    [
        {"source_lat": 12},
        {"source_h3_index": "garbage", "source_location_confidence": "PROFILE_DECLARED"},
        {
            "source_h3_index": h3.latlng_to_cell(12, 77, 7),
            "source_location_confidence": "PROFILE_DECLARED",
        },
        {"source_h3_index": h3.latlng_to_cell(12, 77, 5)},
    ],
)
def test_invalid_geography_rejected(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        m.GeospatialContext.model_validate(data)


def test_gps_and_target_are_independent() -> None:
    target = m.GeospatialContext(target_h3_index=h3.latlng_to_cell(12, 77, 5))
    assert target.source_location_confidence == m.LocationConfidence.UNAVAILABLE
    gps = m.GeospatialContext(
        source_lat=12,
        source_lon=77,
        source_h3_index=h3.latlng_to_cell(12, 77, 5),
        source_location_confidence="EXPLICIT_GPS",
    )
    assert gps.source_lat == 12


def test_report_unavailability_and_additive_contributions() -> None:
    base = dict(
        computation_mode="COMPUTED_PIPELINE",
        parameter_set_id="test",
        coverage_ratio=1,
        evidence_reasons=["Measured repeated links"],
        matched_peer_count=1,
        repeated_bucket_count=2,
    )
    valid = m.AccountSyncAssessment(
        **base, analysis_status="AVAILABLE", sync_score=0.7, feature_contributions={"peer": 0.7}
    )
    assert valid.sync_score == 0.7
    for changes in [
        {"analysis_status": "FAILED", "sync_score": 0},
        {"analysis_status": "AVAILABLE", "sync_score": None},
        {"analysis_status": "AVAILABLE", "sync_score": 0.7, "feature_contributions": {"peer": 0.8}},
        {"analysis_status": "INSUFFICIENT_DATA", "computation_mode": "SIMULATED_FIXTURE_METADATA"},
        {"analysis_status": "INSUFFICIENT_DATA", "feature_contributions": {"bad": float("nan")}},
    ]:
        with pytest.raises(ValidationError):
            m.AccountSyncAssessment.model_validate({**base, **changes})


def test_media_bounds_hashes_and_job_pairings() -> None:
    with pytest.raises(ValidationError):
        m.HeatmapRegion(x=0.8, y=0, w=0.3, h=1, intensity=1, label="outside")
    with pytest.raises(ValidationError):
        m.MediaAttachment(media_id="one", media_type="image", collection_status="COLLECTED")
    with pytest.raises(ValidationError):
        m.JobStatusResponse(job_id="one", job_type="SCENARIO", status="SUCCEEDED")
    with pytest.raises(ValidationError):
        m.JobStatusResponse(job_id="one", job_type="SCENARIO", status="FAILED")
    with pytest.raises(ValidationError):
        m.WebSocketStreamMessage(
            sequence=1,
            message_type="SCENARIO_RESET",
            timestamp_utc=datetime.now(UTC),
            headline="Reset",
            payload=m.JobNotification(job_id="one", status="SUCCEEDED"),
        )


def test_claim_review_requires_context() -> None:
    with pytest.raises(ValidationError):
        m.ClaimVerificationAssessment(
            computation_mode="HEURISTIC_INDICATOR",
            analysis_status="AVAILABLE",
            parameter_set_id="test",
            coverage_ratio=1,
            evidence_reasons=["Retrieved a candidate"],
            status="CORROBORATED",
        )
