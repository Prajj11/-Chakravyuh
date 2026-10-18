"""Cross-field invariants shared by all wire models; repository context adds further checks."""

from math import isclose, isfinite

import h3


def validate_contract(value: object) -> None:
    from app.schemas import models as m

    if isinstance(value, m.ScenarioSwitchRequest):
        from app.ingestion.case_catalogue import DEMO_CASE_IDS

        if value.scenario_id not in (
            "cmp_electoral_01",
            "cmp_geo_astroturf_02",
            "cmp_organic_03",
            "all",
            "expanded",
            *DEMO_CASE_IDS,
        ):
            raise ValueError("Unknown replay scenario")
    if isinstance(value, m.AnalyticalReport):
        if value.computation_mode == m.ComputationMode.SIMULATED_FIXTURE_METADATA:
            raise ValueError("Fixture annotations cannot be analytical reports")
        if not all(isfinite(number) for number in value.feature_contributions.values()):
            raise ValueError("Contributions must be finite")
        primary = {
            "BotAssessment": "bot_indicator_score",
            "AccountSyncAssessment": "sync_score",
            "CoordinationAssessment": "sync_score",
            "ForensicMediaReport": "manipulation_indicator_score",
            "HarmAssessment": "harm_indicator_score",
            "CampaignThreatBreakdown": "cti_score",
        }.get(type(value).__name__)
        if primary:
            score = getattr(value, primary)
            available = value.analysis_status == m.AnalysisStatus.AVAILABLE
            if available != (score is not None):
                raise ValueError("Primary score must be present exactly when analysis is AVAILABLE")
            if type(value).__name__ in {
                "BotAssessment",
                "AccountSyncAssessment",
                "CoordinationAssessment",
                "CampaignThreatBreakdown",
            }:
                if score is not None and not isclose(
                    sum(value.feature_contributions.values()), score, abs_tol=1e-8
                ):
                    raise ValueError("Additive contributions must sum to the primary score")
    if isinstance(value, m.MediaAttachment):
        collected = value.collection_status == "COLLECTED"
        if collected != (value.sha256_hash is not None and value.evidence_ref is not None):
            raise ValueError("Collected media requires both byte hash and evidence reference")
        if not collected and (value.sha256_hash is not None or value.evidence_ref is not None):
            raise ValueError("Uncollected media cannot claim retained evidence")
    if isinstance(value, (m.GeospatialContext, m.EventInjectRequest)):
        if (value.source_lat is None) != (value.source_lon is None):
            raise ValueError("Source coordinates must be a pair")
    if isinstance(value, m.GeospatialContext):
        for cell in (value.source_h3_index, value.target_h3_index):
            if cell is not None and (not h3.is_valid_cell(cell) or h3.get_resolution(cell) != 5):
                raise ValueError("Geographic cells must be valid H3 resolution 5")
        known = value.source_location_confidence != m.LocationConfidence.UNAVAILABLE
        if known != (value.source_h3_index is not None):
            raise ValueError("Known source geography requires an H3 cell and source confidence")
        if value.source_location_confidence == m.LocationConfidence.EXPLICIT_GPS:
            if value.source_lat is None:
                raise ValueError("Explicit GPS requires coordinates")
            if h3.latlng_to_cell(value.source_lat, value.source_lon, 5) != value.source_h3_index:
                raise ValueError("GPS and H3 cell disagree")
        if not known and value.source_lat is not None:
            raise ValueError("Coordinates cannot be labelled unavailable")
    if isinstance(value, m.UnifiedSocialEvent):
        if not value.account.account_id.startswith(value.platform.value + ":"):
            raise ValueError("Account identity must be platform-qualified")
        if value.target_account_id and not value.target_account_id.startswith(
            value.platform.value + ":"
        ):
            raise ValueError("Target identity must be platform-qualified")
        if (
            value.raw_capture_format == "HTTP_ENTITY_BYTES"
            and value.data_origin != m.DataOrigin.PUBLIC_OSINT
        ):
            raise ValueError("Replay/injection must use canonical source captures")
    if isinstance(value, m.HeatmapRegion):
        if value.x + value.w > 1 + 1e-12 or value.y + value.h > 1 + 1e-12:
            raise ValueError("Heatmap region extends beyond image")
    if isinstance(value, m.CoordinationAssessment):
        if (
            value.hawkes_status == m.AnalysisStatus.UNSUPPORTED
            and value.hawkes_branching_ratio is not None
        ):
            raise ValueError("Unsupported Hawkes cannot carry an estimate")
    if isinstance(value, m.ClaimReference) and value.synthetic_reference:
        if (
            not value.source_title.startswith("Synthetic demo advisory")
            or value.source_url is not None
        ):
            raise ValueError("Synthetic references need a visible label and local snapshot")
    if isinstance(value, m.ClaimVerificationAssessment):
        if (value.reviewed_by is None) != (value.reviewed_at_utc is None):
            raise ValueError("Reviewer and review timestamp must be supplied together")
        if value.status != m.ClaimVerificationStatus.UNVERIFIED:
            if (
                not value.reviewed_by
                or not value.candidate_reference
                or not value.analyst_note.strip()
            ):
                raise ValueError("Reviewed claims need reference, reviewer, time and context note")
    if isinstance(value, m.CampaignThreatBreakdown):
        if value.cti_score is None:
            if value.threat_level is not None or value.alert_eligible:
                raise ValueError("Unavailable CTI has no tier or alert")
        else:
            expected = (
                m.ThreatLevel.LOW
                if value.cti_score < 40
                else m.ThreatLevel.MEDIUM
                if value.cti_score < 60
                else m.ThreatLevel.HIGH
                if value.cti_score < 75
                else m.ThreatLevel.CRITICAL
            )
            if value.threat_level != expected or value.sync_component is None:
                raise ValueError("CTI requires sync and correct unrounded tier")
            if not isclose(sum(value.effective_weights.values()), 1, abs_tol=1e-8):
                raise ValueError("Effective CTI weights must sum to one")
            if value.alert_eligible and (
                value.cti_score < 75
                or value.coverage_ratio < 0.60
                or value.sync_component < 65
                or value.scored_post_coverage_ratio < 0.30
            ):
                raise ValueError("Alert eligibility requires score and coverage gates")
    if isinstance(value, m.JobStatusResponse):
        expected_type = {
            "SCENARIO": m.ScenarioSwitchResponse,
            "INJECT": m.UnifiedSocialEventEnriched,
            "FORENSICS": m.ForensicMediaReport,
            "EXPORT": m.EvidenceDossierBundle,
        }[value.job_type]
        if value.status == "SUCCEEDED":
            if not isinstance(value.result, expected_type) or value.error_code is not None:
                raise ValueError("Successful job requires its typed result and no error")
        elif value.result is not None or value.artifact_download_url is not None:
            raise ValueError("Incomplete/failed jobs cannot contain successful results")
        if value.status == "FAILED" and not value.error_code:
            raise ValueError("Failed job requires an error code")
        if value.status in {"QUEUED", "RUNNING"} and value.error_code is not None:
            raise ValueError("An active job cannot contain a failure code")
    if isinstance(value, m.WebSocketStreamMessage):
        expected_type = {
            "NEW_EVENT": m.UnifiedSocialEventEnriched,
            "CTI_ALERT": m.CampaignAlert,
            "SCENARIO_RESET": m.ScenarioSwitchResponse,
            "JOB_UPDATED": m.JobNotification,
        }[value.message_type]
        if not isinstance(value.payload, expected_type):
            raise ValueError("WebSocket message requires its matching payload")
