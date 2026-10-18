from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    model_validator,
)

SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


def utc_string(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


UTCDateTime = Annotated[
    AwareDatetime, PlainSerializer(utc_string, return_type=str, when_used="json")
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        from app.schemas.validation import validate_contract

        validate_contract(self)
        return self


class PlatformType(StrEnum):
    X_TWITTER = "x_twitter"
    TELEGRAM = "telegram"
    REDDIT = "reddit"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    SIMULATOR = "simulator"


class InteractionType(StrEnum):
    ORIGINAL_POST = "original_post"
    REPOST = "repost"
    QUOTE = "quote"
    REPLY = "reply"
    CO_HASHTAG = "co_hashtag"


class AccountRole(StrEnum):
    EARLIEST_OBSERVED_SEED = "EARLIEST_OBSERVED_SEED"
    BOT_AMPLIFIER = "BOT_AMPLIFIER"
    BRIDGE_INFLUENCER = "BRIDGE_INFLUENCER"
    ORGANIC_USER = "ORGANIC_USER"
    UNCLASSIFIED = "UNCLASSIFIED"


class ThreatLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class HarmCategory(StrEnum):
    COMMUNAL_INCITEMENT = "COMMUNAL_INCITEMENT"
    ELECTORAL_MANIPULATION = "ELECTORAL_MANIPULATION"
    PUBLIC_PANIC = "PUBLIC_PANIC"
    INSTITUTIONAL_DISCREDIT = "INSTITUTIONAL_DISCREDIT"
    BENIGN = "BENIGN"


class ClaimVerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED_BY_SOURCE = "CONTRADICTED_BY_SOURCE"
    CORROBORATED = "CORROBORATED"
    CONTEXT_MISSING = "CONTEXT_MISSING"


class LocationConfidence(StrEnum):
    EXPLICIT_GPS = "EXPLICIT_GPS"
    PROFILE_DECLARED = "PROFILE_DECLARED"
    UNAVAILABLE = "UNAVAILABLE"


class ComputationMode(StrEnum):
    COMPUTED_PIPELINE = "COMPUTED_PIPELINE"
    COMPUTED_ELA_PHASH = "COMPUTED_ELA_PHASH"
    HEURISTIC_INDICATOR = "HEURISTIC_INDICATOR"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    SIMULATED_FIXTURE_METADATA = "SIMULATED_FIXTURE_METADATA"


class DataOrigin(StrEnum):
    PUBLIC_OSINT = "PUBLIC_OSINT"
    USER_INJECTED = "USER_INJECTED"
    SYNTHETIC_REPLAY = "SYNTHETIC_REPLAY"


class AnalysisStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"
    PENDING = "PENDING"


class C2PAStatus(StrEnum):
    NOT_CHECKED = "NOT_CHECKED"
    MISSING = "MISSING"
    VALID = "VALID"
    INVALID = "INVALID"
    UNSUPPORTED = "UNSUPPORTED"


class AnalyticalReport(ContractModel):
    computation_mode: ComputationMode
    analysis_status: AnalysisStatus
    pipeline_version: str = "2.1.0"
    parameter_set_id: str
    coverage_ratio: float = Field(ge=0, le=1)
    missing_signals: list[str] = Field(default_factory=list)
    evidence_reasons: list[str] = Field(min_length=1)
    feature_contributions: dict[str, float] = Field(default_factory=dict)


class MediaAttachment(ContractModel):
    media_id: str
    media_type: Literal["image", "video", "audio"]
    url: str | None = None
    sha256_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    evidence_ref: str | None = None
    collection_status: Literal["COLLECTED", "UNAVAILABLE", "PENDING"]
    # Perceptual hashes are computed enrichment in ForensicMediaReport.


class AccountProfile(ContractModel):
    account_id: str
    handle: str
    display_name: str | None = None
    created_at: UTCDateTime | None = None
    followers_count: int | None = Field(default=None, ge=0)
    following_count: int | None = Field(default=None, ge=0)
    profile_location: str | None = None
    is_verified: bool | None = None


class GeospatialContext(ContractModel):
    source_lat: float | None = Field(default=None, ge=-90, le=90)
    source_lon: float | None = Field(default=None, ge=-180, le=180)
    source_region_name: str | None = None
    source_h3_index: str | None = None
    source_location_confidence: LocationConfidence = LocationConfidence.UNAVAILABLE
    target_region_name: str | None = None
    target_h3_index: str | None = None
    # Mentioned subject locations never become author source locations.


class UnifiedSocialEvent(ContractModel):
    event_id: str
    platform: PlatformType
    data_origin: DataOrigin
    source_url: str | None = None
    timestamp_utc: UTCDateTime
    collection_timestamp_utc: UTCDateTime
    collector_id: str
    raw_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_payload_ref: str
    raw_capture_manifest_ref: str
    raw_capture_format: Literal["HTTP_ENTITY_BYTES", "CANONICAL_JSON_V1"]
    canonical_event_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonicalization_version: Literal["canonical-json-v1"] = "canonical-json-v1"
    account: AccountProfile
    text: str
    language: str = "und"
    hashtags: tuple[str, ...] = ()
    urls: tuple[str, ...] = ()
    media_attachments: tuple[MediaAttachment, ...] = ()
    interaction_type: InteractionType = InteractionType.ORIGINAL_POST
    parent_event_id: str | None = None
    target_account_id: str | None = None
    geospatial: GeospatialContext = Field(default_factory=GeospatialContext)
    # Campaign membership and later enrichment live outside this immutable record.


class ClaimReference(ContractModel):
    reference_id: str
    claim_text: str
    finding: ClaimVerificationStatus
    source_title: str
    source_url: str | None = None
    published_at_utc: UTCDateTime
    retrieved_at_utc: UTCDateTime
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshot_ref: str
    languages: list[str]
    applicable_region: str | None = None
    valid_until_utc: UTCDateTime | None = None
    synthetic_reference: bool = False


class ClaimVerificationAssessment(AnalyticalReport):
    status: ClaimVerificationStatus = ClaimVerificationStatus.UNVERIFIED
    candidate_reference: ClaimReference | None = None
    similarity_to_known_claim: float | None = Field(default=None, ge=0, le=1)
    reviewed_by: str | None = None
    reviewed_at_utc: UTCDateTime | None = None
    analyst_note: str = "Coordination indicators do not establish claim falsity."


class BotAssessment(AnalyticalReport):
    bot_indicator_score: float | None = Field(default=None, ge=0, le=100)
    observed_posts: int = Field(ge=0)
    observation_seconds: float = Field(ge=0)
    available_feature_weights: dict[str, float]


class AccountSyncAssessment(AnalyticalReport):
    sync_score: float | None = Field(default=None, ge=0, le=1)
    matched_peer_count: int = Field(ge=0)
    repeated_bucket_count: int = Field(ge=0)
    mean_matched_delta_sec: float | None = Field(default=None, ge=0)


class CoordinationAssessment(AnalyticalReport):
    sync_score: float | None = Field(default=None, ge=0, le=1)
    eligible_pair_count: int = Field(ge=0)
    coordinated_account_count: int = Field(ge=0)
    total_account_count: int = Field(ge=0)
    burst_index: float | None = Field(default=None, ge=0)
    hawkes_branching_ratio: float | None = Field(default=None, ge=0)
    hawkes_status: AnalysisStatus = AnalysisStatus.UNSUPPORTED
    # A computed burst_index is never represented as a fitted Hawkes estimate.


class HeatmapRegion(ContractModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)
    intensity: float = Field(ge=0, le=1)
    label: str


class ForensicMediaReport(AnalyticalReport):
    media_id: str
    media_type: Literal["image", "video", "audio"]
    phash: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    duplicate_matches_count: int = Field(ge=0)
    manipulation_indicator_score: float | None = Field(default=None, ge=0, le=100)
    ela_anomaly_score: float | None = Field(default=None, ge=0, le=100)
    deepfake_visual_score: float | None = Field(default=None, ge=0, le=100)
    model_id: str | None = None
    model_revision: str | None = None
    calibration_id: str | None = None
    audio_sync_drift_ms: float | None = None
    exif_present: bool | None = None
    c2pa_status: C2PAStatus = C2PAStatus.NOT_CHECKED
    heatmap_regions: list[HeatmapRegion] = Field(default_factory=list)
    heatmap_artifact_ref: str | None = None


class GraphNode(AnalyticalReport):
    id: str
    handle: str
    role: AccountRole
    bot_assessment: BotAssessment
    sync_assessment: AccountSyncAssessment
    posts_in_campaign: int = Field(ge=1)
    community_id: int
    betweenness_centrality: float = Field(ge=0, le=1)
    cascade_out_degree: int = Field(ge=0)
    region: str | None = None
    account_created_at: UTCDateTime | None = None
    first_observed_utc: UTCDateTime


class GraphEdge(AnalyticalReport):
    source: str
    target: str
    interaction_type: Literal["CO_POST_SYNC", "REPOST_CASCADE", "BRIDGE_TRANSFER", "ORGANIC_REPLY"]
    sync_weight: float | None = Field(default=None, ge=0, le=1)
    matched_event_ids: list[str]
    time_delta_sec: float | None = Field(default=None, ge=0)


class SourceOrigin(ContractModel):
    source_h3_index: str
    source_region: str | None = None
    source_location_confidence: LocationConfidence
    latitude: float
    longitude: float
    post_count: int = Field(ge=1)


class GeoHexAnomaly(AnalyticalReport):
    h3_index: str
    baseline_scope_id: str
    window_end_utc: UTCDateTime
    h3_resolution: Literal[5] = 5
    region_name: str | None = None
    latitude: float
    longitude: float
    current_velocity_1hr: int = Field(ge=0)
    target_campaign_posts_1hr: int = Field(ge=0)
    baseline_mean_1hr: float | None = None
    baseline_std_1hr: float | None = Field(default=None, ge=0)
    baseline_bucket_count: int = Field(ge=0)
    baseline_status: AnalysisStatus
    baseline_data_origin: DataOrigin | None = None
    z_score: float | None = None
    source_location_coverage_ratio: float = Field(ge=0, le=1)
    known_source_posts: int = Field(ge=0)
    known_source_accounts: int = Field(ge=0)
    geospatial_mismatch_ratio: float | None = Field(default=None, ge=0, le=1)
    coordination_sync_score: float | None = Field(default=None, ge=0, le=1)
    is_astroturfing_alert: bool
    top_source_origins: list[SourceOrigin] = Field(default_factory=list)


class HarmAssessment(AnalyticalReport):
    category: HarmCategory
    harm_indicator_score: float | None = Field(default=None, ge=0, le=100)


class NarrativeCluster(ContractModel):
    campaign_id: str
    event_ids: list[str]
    embedding_mode: ComputationMode
    embedding_model_id: str
    embedding_revision: str
    centroid: list[float]
    first_detected_utc: UTCDateTime
    last_updated_utc: UTCDateTime


class TimelineBucket(ContractModel):
    timestamp_utc: UTCDateTime
    coordinated_volume: int = Field(ge=0)
    low_indicator_volume: int = Field(ge=0)
    unclassified_volume: int = Field(ge=0)
    burst_index: float | None = Field(default=None, ge=0)


class CampaignThreatBreakdown(AnalyticalReport):
    cti_score: float | None = Field(default=None, ge=0, le=100)
    threat_level: ThreatLevel | None = None
    sync_component: float | None = Field(default=None, ge=0, le=100)
    bot_density_component: float | None = Field(default=None, ge=0, le=100)
    media_forensics_component: float | None = Field(default=None, ge=0, le=100)
    geo_anomaly_component: float | None = Field(default=None, ge=0, le=100)
    harm_severity_component: float | None = Field(default=None, ge=0, le=100)
    component_modes: dict[str, ComputationMode]
    effective_weights: dict[str, float]
    scored_post_coverage_ratio: float = Field(ge=0, le=1)
    alert_eligible: bool
    alert_suppression_reasons: list[str] = Field(default_factory=list)


class CollectionWindowMetadata(ContractModel):
    window_start_utc: UTCDateTime
    window_end_utc: UTCDateTime
    collector_sources: list[str]
    coverage_completeness_note: str = (
        "Seed attribution is bounded by collected data; no global origin is established."
    )


class NarrativeCampaignSummary(ContractModel):
    campaign_id: str
    snapshot_revision: int = Field(ge=1)
    title: str
    primary_narrative_claim: str
    data_origin: DataOrigin
    claim_verification: ClaimVerificationAssessment
    collection_window: CollectionWindowMetadata
    languages: list[str]
    first_detected_utc: UTCDateTime
    last_updated_utc: UTCDateTime
    total_posts: int = Field(ge=0)
    total_accounts: int = Field(ge=0)
    bot_accounts_count: int = Field(ge=0)
    earliest_seed_handle: str | None = None
    coordination_assessment: CoordinationAssessment
    cti_assessment: CampaignThreatBreakdown
    has_media_indicators: bool
    has_geo_astroturfing: bool


class NarrativeCampaignDetail(NarrativeCampaignSummary):
    sample_posts: list[UnifiedSocialEvent]
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    timeline: list[TimelineBucket]
    geo_anomalies: list[GeoHexAnomaly]
    media_reports: list[ForensicMediaReport]
    harm_assessment: HarmAssessment


class AuditTrailEntry(ContractModel):
    entry_id: str
    action: Literal["INGEST", "MEDIA_COLLECTED", "ANALYZE", "CLAIM_REVIEW", "EXPORT", "VERIFY"]
    timestamp_utc: UTCDateTime
    actor_id: str
    event_id: str | None = None
    collector_id: str | None = None
    collection_timestamp_utc: UTCDateTime | None = None
    raw_payload_sha256: SHA256 | None = None
    canonical_event_sha256: SHA256 | None = None
    media_sha256: list[SHA256] = Field(default_factory=list)
    artifact_sha256: list[SHA256] = Field(default_factory=list)
    previous_entry_sha256: SHA256 | None = None
    entry_sha256: SHA256
    pipeline_version: str = "2.1.0"
    parameter_set_id: str
    input_data_origin: DataOrigin
    verification_status: Literal["NOT_CHECKED", "VERIFIED", "MISMATCH", "UNAVAILABLE"]


class EvidenceArtifact(ContractModel):
    artifact_id: str
    artifact_kind: Literal[
        "RAW_PAYLOAD", "CANONICAL_EVENT", "MEDIA", "ANALYSIS", "REFERENCE", "REPORT"
    ]
    sha256_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_ref: str
    representation: Literal["ORIGINAL", "REDACTED_DERIVATIVE"]
    original_sha256: str | None = None


class EvidenceDossierBundle(ContractModel):
    dossier_id: str
    generated_at_utc: UTCDateTime
    pipeline_version: str = "2.1.0"
    parameter_set_id: str
    redacted_pii: bool
    campaign_summary: NarrativeCampaignSummary
    key_coordination_findings: list[str]
    media_forensic_reports: list[ForensicMediaReport]
    audit_manifest: list[AuditTrailEntry]
    artifacts: list[EvidenceArtifact]
    stix2_bundle_json: dict[str, object]
    integrity_disclaimer: str = (
        "Hashes detect changes relative to this manifest. They establish neither content truth "
        "nor legal admissibility; external anchoring is outside the MVP."
    )


class HealthStatusResponse(ContractModel):
    status: Literal["healthy", "degraded"]
    pipeline_version: str = "2.1.0"
    active_campaigns_count: int = Field(ge=0)
    total_ingested_events: int = Field(ge=0)
    layer_status: dict[str, AnalysisStatus]
    execution_mode: Literal["local_computed"] = "local_computed"


class ScenarioSwitchRequest(ContractModel):
    scenario_id: str = Field(min_length=1, max_length=80)
    reset_state: bool = True
    seed: int = 42
    speed_multiplier: float = Field(default=1, gt=0, le=100)
    playback_mode: Literal["TIMED", "BATCH"] = "TIMED"


class ScenarioSwitchResponse(ContractModel):
    scenario_id: str
    loaded_campaign_ids: list[str]
    reset_state: bool


class EventInjectRequest(ContractModel):
    handle: str = "@Custom_Test_Account"
    account_id: str | None = None
    text: str = Field(min_length=1, max_length=20000)
    language: str = "und"
    timestamp_utc: UTCDateTime | None = None
    source_lat: float | None = Field(default=None, ge=-90, le=90)
    source_lon: float | None = Field(default=None, ge=-180, le=180)
    profile_location: str | None = None
    target_region_name: str | None = None
    media_artifact_ids: list[str] = Field(default_factory=list)
    # Server assigns SIMULATOR platform and USER_INJECTED origin.
    # Injection cannot impersonate a public connector or attach fixture-only annotations.


class MediaUploadResponse(ContractModel):
    media_artifact_id: str
    sha256_hash: str
    media_type: Literal["image", "video", "audio"]


class ForensicsVerifyRequest(ContractModel):
    media_artifact_id: str


class UnifiedSocialEventEnriched(ContractModel):
    event: UnifiedSocialEvent
    assigned_campaign_id: str
    bot_assessment: BotAssessment
    sync_assessment: AccountSyncAssessment
    updated_campaign_cti: CampaignThreatBreakdown
    triggered_critical_alert: bool


class ClaimReviewRequest(ContractModel):
    reference_id: str
    status: ClaimVerificationStatus
    analyst_note: str = Field(min_length=1)


class ExportRequest(ContractModel):
    format: Literal["bundle", "pdf", "html", "stix"] = "bundle"
    redact_pii: bool = True


class JobAccepted(ContractModel):
    job_id: str
    status_url: str


class JobStatusResponse(ContractModel):
    job_id: str
    job_type: Literal["SCENARIO", "INJECT", "FORENSICS", "EXPORT"]
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED"]
    result: (
        ScenarioSwitchResponse
        | UnifiedSocialEventEnriched
        | ForensicMediaReport
        | EvidenceDossierBundle
        | None
    ) = None
    artifact_download_url: str | None = None
    error_code: str | None = None


class APIError(ContractModel):
    code: str
    message: str
    request_id: str


class CampaignAlert(ContractModel):
    campaign_id: str
    assessment: CampaignThreatBreakdown


class JobNotification(ContractModel):
    job_id: str
    status: Literal["SUCCEEDED", "FAILED"]


class WebSocketStreamMessage(ContractModel):
    sequence: int = Field(ge=1)
    message_type: Literal["NEW_EVENT", "CTI_ALERT", "SCENARIO_RESET", "JOB_UPDATED"]
    timestamp_utc: UTCDateTime
    campaign_id: str | None = None
    headline: str
    payload: UnifiedSocialEventEnriched | CampaignAlert | ScenarioSwitchResponse | JobNotification
