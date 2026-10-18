"""Available-component prioritization and event-time transition gating."""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.config import Parameters
from app.schemas.models import (
    AnalysisStatus,
    BotAssessment,
    CampaignThreatBreakdown,
    ComputationMode,
    CoordinationAssessment,
    ForensicMediaReport,
    GeoHexAnomaly,
    HarmAssessment,
    ThreatLevel,
    UnifiedSocialEvent,
)


def threat_level(score: float, p: Parameters) -> ThreatLevel:
    return (
        ThreatLevel.LOW
        if score < p.CTI_MEDIUM_THRESHOLD
        else ThreatLevel.MEDIUM
        if score < p.CTI_HIGH_THRESHOLD
        else ThreatLevel.HIGH
        if score < p.CTI_CRITICAL_ALERT_THRESHOLD
        else ThreatLevel.CRITICAL
    )


def compute_cti(
    p: Parameters,
    events: Sequence[UnifiedSocialEvent],
    coordination: CoordinationAssessment,
    bots: dict[str, BotAssessment],
    media: Sequence[ForensicMediaReport],
    geo: Sequence[GeoHexAnomaly],
    harm: HarmAssessment,
) -> CampaignThreatBreakdown:
    counts = Counter(event.account.account_id for event in events)
    scored = {
        author: bot
        for author, bot in bots.items()
        if bot.analysis_status == AnalysisStatus.AVAILABLE and author in counts
    }
    scored_posts = sum(counts[author] for author in scored)
    scored_coverage = scored_posts / len(events) if events else 0
    bot_density = (
        100
        * sum(
            counts[author]
            for author, bot in scored.items()
            if bot.bot_indicator_score is not None
            and bot.bot_indicator_score >= p.BOT_PROBABILITY_HIGH_CUTOFF
        )
        / scored_posts
        if scored_posts
        and scored_coverage >= p.CTI_MIN_SCORED_POST_COVERAGE
        and len(scored) >= p.CTI_BOT_MIN_SCORED_AUTHORS
        else None
    )
    media_values = [
        report.manipulation_indicator_score
        for report in media
        if report.analysis_status == AnalysisStatus.AVAILABLE
        and report.manipulation_indicator_score is not None
    ]
    media_score = (
        max(media_values)
        if media_values
        else None
        if any(event.media_attachments for event in events)
        else 0
    )
    geo_values = [
        100 * min(max(report.z_score, 0) / p.GEO_Z_COMPONENT_SCALE, 1)
        for report in geo
        if report.z_score is not None
    ]
    geo_values += [
        100 * report.geospatial_mismatch_ratio
        for report in geo
        if report.is_astroturfing_alert and report.geospatial_mismatch_ratio is not None
    ]
    components = {
        "sync": 100 * coordination.sync_score if coordination.sync_score is not None else None,
        "bot_density": bot_density,
        "media_forensics": media_score,
        "geo_anomaly": max(geo_values) if geo_values else None,
        "harm_severity": harm.harm_indicator_score,
    }
    available = {key: value for key, value in components.items() if value is not None}
    coverage = sum(p.CTI_WEIGHTS[key] for key in available)
    weights = {key: p.CTI_WEIGHTS[key] / coverage for key in available} if coverage else {}
    sufficient = coverage > 0 and components["sync"] is not None
    contributions = (
        {key: weights[key] * value for key, value in available.items()} if sufficient else {}
    )
    score = min(sum(contributions.values()), 100) if sufficient else None
    gates = {
        "critical_score": score is not None and score >= p.CTI_CRITICAL_ALERT_THRESHOLD,
        "component_coverage": coverage >= p.CTI_MIN_COMPONENT_COVERAGE,
        "campaign_sync": coordination.sync_score is not None
        and coordination.sync_score >= p.BOT_SYNC_SCORE_CUTOFF,
        "scored_post_coverage": scored_coverage >= p.CTI_MIN_SCORED_POST_COVERAGE,
        "campaign_posts": len(events) >= p.ALERT_MIN_CAMPAIGN_POSTS,
        "campaign_authors": len(counts) >= p.ALERT_MIN_CAMPAIGN_AUTHORS,
    }
    return CampaignThreatBreakdown(
        computation_mode=ComputationMode.COMPUTED_PIPELINE,
        analysis_status=AnalysisStatus.AVAILABLE
        if sufficient
        else AnalysisStatus.INSUFFICIENT_DATA,
        parameter_set_id=p.parameter_set_id,
        coverage_ratio=coverage,
        missing_signals=sorted(set(components) - available.keys()),
        evidence_reasons=[
            "Available-component weighted prioritization; "
            "indicators do not establish claim falsity.",
            "Missing components are excluded and effective weights are renormalized.",
        ],
        feature_contributions=contributions,
        cti_score=score,
        threat_level=threat_level(score, p) if score is not None else None,
        sync_component=components["sync"],
        bot_density_component=bot_density,
        media_forensics_component=media_score,
        geo_anomaly_component=components["geo_anomaly"],
        harm_severity_component=components["harm_severity"],
        component_modes={
            key: (
                ComputationMode.HEURISTIC_INDICATOR
                if key in {"bot_density", "harm_severity"}
                else ComputationMode.COMPUTED_ELA_PHASH
                if key == "media_forensics" and media_values
                else ComputationMode.COMPUTED_PIPELINE
            )
            for key in available
        },
        effective_weights=weights,
        scored_post_coverage_ratio=scored_coverage,
        alert_eligible=all(gates.values()),
        alert_suppression_reasons=[key for key, passed in gates.items() if not passed],
    )


@dataclass
class AlertState:
    armed: bool = True
    last_emitted: datetime | None = None
    below_since: datetime | None = None
    watermark: datetime | None = None
    previous_eligible: bool = False

    def observe(
        self, assessment: CampaignThreatBreakdown, timestamp: datetime, p: Parameters
    ) -> bool:
        if self.watermark is not None and timestamp < self.watermark:
            return False
        self.watermark = timestamp
        if assessment.cti_score is not None and assessment.cti_score < p.ALERT_REARM_BELOW:
            self.below_since = self.below_since or timestamp
            if (timestamp - self.below_since).total_seconds() >= p.ALERT_REARM_SEC:
                self.armed = True
        else:
            self.below_since = None
        cooldown = (
            self.last_emitted is None
            or (timestamp - self.last_emitted).total_seconds() >= p.ALERT_COOLDOWN_SEC
        )
        fire = assessment.alert_eligible and not self.previous_eligible and self.armed and cooldown
        self.previous_eligible = assessment.alert_eligible
        if fire:
            self.last_emitted, self.armed = timestamp, False
        return fire
