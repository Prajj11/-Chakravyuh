"""Contextual human claim review; retrieval alone never changes verification status."""

from datetime import UTC, datetime

from app.evidence.canonical import sha256
from app.repositories.state import StateRepository
from app.schemas.models import (
    AnalysisStatus,
    ClaimReviewRequest,
    ClaimVerificationAssessment,
    DataOrigin,
    NarrativeCampaignDetail,
)


def review_claim(
    state: StateRepository,
    campaign: NarrativeCampaignDetail,
    request: ClaimReviewRequest,
    actor: str,
) -> ClaimVerificationAssessment:
    if not actor.startswith("local-analyst:") or not request.analyst_note.strip():
        raise ValueError("Local reviewer and contextual note are required")
    reference = next(
        (
            item
            for item in state.list_claim_references()
            if item.reference_id == request.reference_id
        ),
        None,
    )
    if reference is None or campaign.claim_verification.candidate_reference is None:
        raise ValueError("No retained candidate reference is available")
    if reference.reference_id != campaign.claim_verification.candidate_reference.reference_id:
        raise ValueError("Review must address the retrieved candidate")
    if reference.synthetic_reference and campaign.data_origin != DataOrigin.SYNTHETIC_REPLAY:
        raise ValueError("Synthetic advisories cannot verify injected/public claims")
    if reference.published_at_utc > campaign.last_updated_utc or (
        reference.valid_until_utc is not None
        and reference.valid_until_utc < campaign.first_detected_utc
    ):
        raise ValueError("The reference is outside the observed claim period")
    regions = {event.geospatial.target_region_name for event in campaign.sample_posts}
    if reference.applicable_region and reference.applicable_region not in regions:
        raise ValueError("The reference does not address the observed region")
    data, _, kind = state.evidence.artifact(reference.snapshot_ref, state.scope)
    if kind != "REFERENCE" or sha256(data) != reference.snapshot_sha256:
        raise ValueError("The retained source snapshot differs")
    assessment = ClaimVerificationAssessment.model_validate(
        {
            **campaign.claim_verification.model_dump(),
            "status": request.status,
            "analysis_status": AnalysisStatus.AVAILABLE,
            "reviewed_by": actor,
            "reviewed_at_utc": datetime.now(UTC),
            "analyst_note": request.analyst_note.strip(),
            "candidate_reference": reference,
            "evidence_reasons": [
                "Local analyst reviewed date, region, actors and media context.",
                "The recorded note explains the contextual decision.",
            ],
        }
    )
    with state.evidence.transaction() as db:
        audit = state.evidence.append_audit(
            db,
            action="CLAIM_REVIEW",
            origin=campaign.data_origin,
            actor_id=actor,
            artifact_sha256=[reference.snapshot_sha256],
        )
    state.append_claim_review(campaign.campaign_id, assessment, audit.entry_id)
    return assessment
