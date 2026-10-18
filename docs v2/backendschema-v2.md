# Backend Schemas, Persistence & API Contracts: Chakravyuh

**Contract version:** 2.1.0  
**Updated:** October 18, 2026  
**Status:** Authoritative contract. Models and evidence foundation implemented; analytical services and full API remain pending (see tasks-v2.md).

This file owns wire names, enums, response shapes, and storage contracts. [trd-v2.md](trd-v2.md) owns algorithms and constants. All v2 files supersede v1; no implicit inheritance is required. Keep existing v2 filenames.

## 1. Shared typed models

The following Python 3.11+ / Pydantic v2 definitions form one module. Implement the cross-field invariants in Section 2 as model/service validators. TypeScript mirrors these models with strict types and discriminated unions; arbitrary JSON is limited to the external STIX document.

```python
from enum import Enum
from typing import Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class PlatformType(str, Enum):
    X_TWITTER = "x_twitter"
    TELEGRAM = "telegram"
    REDDIT = "reddit"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    SIMULATOR = "simulator"

class InteractionType(str, Enum):
    ORIGINAL_POST = "original_post"
    REPOST = "repost"
    QUOTE = "quote"
    REPLY = "reply"
    CO_HASHTAG = "co_hashtag"

class AccountRole(str, Enum):
    EARLIEST_OBSERVED_SEED = "EARLIEST_OBSERVED_SEED"
    BOT_AMPLIFIER = "BOT_AMPLIFIER"
    BRIDGE_INFLUENCER = "BRIDGE_INFLUENCER"
    ORGANIC_USER = "ORGANIC_USER"
    UNCLASSIFIED = "UNCLASSIFIED"

class ThreatLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class HarmCategory(str, Enum):
    COMMUNAL_INCITEMENT = "COMMUNAL_INCITEMENT"
    ELECTORAL_MANIPULATION = "ELECTORAL_MANIPULATION"
    PUBLIC_PANIC = "PUBLIC_PANIC"
    INSTITUTIONAL_DISCREDIT = "INSTITUTIONAL_DISCREDIT"
    BENIGN = "BENIGN"

class ClaimVerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED_BY_SOURCE = "CONTRADICTED_BY_SOURCE"
    CORROBORATED = "CORROBORATED"
    CONTEXT_MISSING = "CONTEXT_MISSING"

class LocationConfidence(str, Enum):
    EXPLICIT_GPS = "EXPLICIT_GPS"
    PROFILE_DECLARED = "PROFILE_DECLARED"
    UNAVAILABLE = "UNAVAILABLE"

class ComputationMode(str, Enum):
    COMPUTED_PIPELINE = "COMPUTED_PIPELINE"
    COMPUTED_ELA_PHASH = "COMPUTED_ELA_PHASH"
    HEURISTIC_INDICATOR = "HEURISTIC_INDICATOR"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    SIMULATED_FIXTURE_METADATA = "SIMULATED_FIXTURE_METADATA"

class DataOrigin(str, Enum):
    PUBLIC_OSINT = "PUBLIC_OSINT"
    USER_INJECTED = "USER_INJECTED"
    SYNTHETIC_REPLAY = "SYNTHETIC_REPLAY"

class AnalysisStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"
    PENDING = "PENDING"

class C2PAStatus(str, Enum):
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
    created_at: AwareDatetime | None = None
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
    model_config = ConfigDict(extra="forbid", frozen=True)
    event_id: str
    platform: PlatformType
    data_origin: DataOrigin
    source_url: str | None = None
    timestamp_utc: AwareDatetime
    collection_timestamp_utc: AwareDatetime
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
    hashtags: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    media_attachments: list[MediaAttachment] = Field(default_factory=list)
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
    published_at_utc: AwareDatetime
    retrieved_at_utc: AwareDatetime
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshot_ref: str
    languages: list[str]
    applicable_region: str | None = None
    valid_until_utc: AwareDatetime | None = None
    synthetic_reference: bool = False

class ClaimVerificationAssessment(AnalyticalReport):
    status: ClaimVerificationStatus = ClaimVerificationStatus.UNVERIFIED
    candidate_reference: ClaimReference | None = None
    similarity_to_known_claim: float | None = Field(default=None, ge=0, le=1)
    reviewed_by: str | None = None
    reviewed_at_utc: AwareDatetime | None = None
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
    account_created_at: AwareDatetime | None = None
    first_observed_utc: AwareDatetime

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
    window_end_utc: AwareDatetime
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
    first_detected_utc: AwareDatetime
    last_updated_utc: AwareDatetime

class TimelineBucket(ContractModel):
    timestamp_utc: AwareDatetime
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
    window_start_utc: AwareDatetime
    window_end_utc: AwareDatetime
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
    first_detected_utc: AwareDatetime
    last_updated_utc: AwareDatetime
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
    timestamp_utc: AwareDatetime
    actor_id: str
    event_id: str | None = None
    collector_id: str | None = None
    collection_timestamp_utc: AwareDatetime | None = None
    raw_payload_sha256: str | None = None
    canonical_event_sha256: str | None = None
    media_sha256: list[str] = Field(default_factory=list)
    artifact_sha256: list[str] = Field(default_factory=list)
    previous_entry_sha256: str | None = None
    entry_sha256: str
    pipeline_version: str = "2.1.0"
    parameter_set_id: str
    input_data_origin: DataOrigin
    verification_status: Literal["NOT_CHECKED", "VERIFIED", "MISMATCH", "UNAVAILABLE"]

class EvidenceArtifact(ContractModel):
    artifact_id: str
    artifact_kind: Literal["RAW_PAYLOAD", "CANONICAL_EVENT", "MEDIA", "ANALYSIS", "REFERENCE", "REPORT"]
    sha256_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_ref: str
    representation: Literal["ORIGINAL", "REDACTED_DERIVATIVE"]
    original_sha256: str | None = None

class EvidenceDossierBundle(ContractModel):
    dossier_id: str
    generated_at_utc: AwareDatetime
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
    scenario_id: Literal["cmp_electoral_01", "cmp_geo_astroturf_02", "cmp_organic_03", "all"]
    reset_state: bool = True
    seed: int = 42
    speed_multiplier: float = Field(default=1, gt=0, le=100)

class ScenarioSwitchResponse(ContractModel):
    scenario_id: str
    loaded_campaign_ids: list[str]
    reset_state: bool

class EventInjectRequest(ContractModel):
    handle: str = "@Custom_Test_Account"
    account_id: str | None = None
    text: str = Field(min_length=1, max_length=20000)
    language: str = "und"
    timestamp_utc: AwareDatetime | None = None
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
    result: ScenarioSwitchResponse | UnifiedSocialEventEnriched | ForensicMediaReport | EvidenceDossierBundle | None = None
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
    timestamp_utc: AwareDatetime
    campaign_id: str | None = None
    headline: str
    payload: UnifiedSocialEventEnriched | CampaignAlert | ScenarioSwitchResponse | JobNotification
```

## 2. Required invariants

- UTC-aware timestamps serialize as ISO 8601 with `Z`. Scores use unrounded values for thresholds; round only presentation.
- Non-AVAILABLE analytical results carry null primary scores and a reason, except independent sub-results may remain AVAILABLE in their own nested report. Empty graphs are valid; absence is never fabricated zero evidence.
- Collected media require both exact-byte hash and immutable evidence reference. Unavailable/pending media have neither; later fetches create an append-only media collection record and forensic report, not an event mutation.
- An event hash covers its complete initial model serialization excluding only `canonical_event_sha256`. Its nested lists/objects must also be treated as immutable; Pydantic's frozen flag alone does not freeze them.
- GPS fields occur as a valid pair. Known author geography requires a validated H3 cell, resolution 5, and GPS or a resolvable declared profile. Ambiguous/free-text locations remain unknown. Target mentions never supply author geography.
- All reports carry metadata from AnalyticalReport, including graph edges. Bot contributions sum to the score; CTI contributions sum to CTI; synchronization contributions sum to synchronization. Other reports define named intermediate indicators rather than claiming additive SHAP values.
- Role precedence, sufficiency tests, and all-missing behavior follow the TRD. Null bot scores cannot satisfy either bot or organic eligibility.
- Confirmed claim status requires reviewer/time, a context-valid reference, and an audit entry. Candidate similarity alone leaves status UNVERIFIED. Synthetic references can support only SYNTHETIC_REPLAY campaigns, visibly labelled.
- `SIMULATED_FIXTURE_METADATA` is for separate test annotations, never measured analytical scores, CTI inputs, alerts, or real claim verification. Input origin and computation method are independent.
- Bounding boxes satisfy `x+w<=1`, `y+h<=1`. C2PA validity requires cryptographic validation by the adapter; it is independent of capture device or claim truth.
- Job type determines result type; WebSocket message type determines payload type in the listed order. Enforce these pairings, non-null success results, and monotonic sequence numbers with validators.
- Audit hash fields use lowercase 64-hex validation, including optional fields and list items. Raw evidence refs are opaque server-resolved identifiers, never arbitrary client filesystem paths.
- `has_media_indicators` means a measured indicator >=50, not established manipulation. Non-AVAILABLE media never set it true.

## 3. REST and WebSocket endpoints

All paths are authoritative. Heavy work is queued; mutation endpoints return HTTP 202 with JobAccepted. Read endpoints return 200. A completed job returns its typed result; downloads use immutable artifact IDs. Clients can poll jobs even without WebSocket.

| Method | Endpoint | Request | Response / behavior |
|---|---|---|---|
| GET | /api/v1/health | none | HealthStatusResponse |
| GET | /api/v1/campaigns | none | list[NarrativeCampaignSummary], CTI descending, nulls last |
| GET | /api/v1/campaigns/{campaign_id} | none | NarrativeCampaignDetail |
| POST | /api/v1/simulate/scenario | ScenarioSwitchRequest | JobAccepted; result ScenarioSwitchResponse |
| POST | /api/v1/events/inject | EventInjectRequest | JobAccepted; result UnifiedSocialEventEnriched |
| POST | /api/v1/media | multipart file | MediaUploadResponse, HTTP 201; hash/store bytes, no heavy inference |
| POST | /api/v1/forensics/verify-media | ForensicsVerifyRequest | JobAccepted; result ForensicMediaReport |
| GET | /api/v1/jobs/{job_id} | none | JobStatusResponse |
| PUT | /api/v1/campaigns/{campaign_id}/claim-review | ClaimReviewRequest | ClaimVerificationAssessment; reviewer derived from session |
| POST | /api/v1/campaigns/{campaign_id}/export | ExportRequest | JobAccepted; result EvidenceDossierBundle and download URL |
| GET | /api/v1/artifacts/{artifact_id}/download | none | authenticated binary artifact; Content-Type and Content-Disposition |
| WS | /ws/stream | session; optional last_sequence | WebSocketStreamMessage |

Errors use APIError: 400 invalid context, 401/403 access failure, 404 unknown resource, 409 conflicting reset/claim review, 413 size, 415 media type, 422 validation, 429 limit, 500 unexpected failure. Adapt FastAPI validation errors into this envelope. Known job execution failures live in JobStatusResponse with safe error codes.

WebSocket retains the most recent 1,000 messages per session. On an expired sequence, send SCENARIO_RESET with current campaign IDs and require a REST resync. Serialize resets against queued mutations; jobs from the old generation are cancelled/failed explicitly. Poll every 3 seconds after disconnect, reconnect at 1/2/4/8 seconds capped at 30 seconds.

## 4. Persistence and export contracts

Use SQLite for metadata, event membership, jobs, claim reviews, and append-only audit records; raw bytes and canonical JSON live in a content-addressed evidence directory. NumPy vectors and NetworkX graphs are rebuildable indexes. PostgreSQL, Qdrant, Neo4j, and Redis are optional adapters after MVP.

| Store/table | Required identity and fields |
|---|---|
| events | event_id PK; unique (collector_id, raw_payload_sha256, source_event_key); canonical_event_sha256; both evidence refs; timestamp; platform-qualified account_id; data_origin; immutable event JSON |
| campaign_memberships | (campaign_id,event_id) PK; assigned_at; pipeline_version; revision |
| accounts | (platform,account_id) PK; immutable snapshots linked through events |
| campaigns | campaign_id PK; typed summary JSON; revision; latest assessment hash |
| analytical_runs | run_id PK; input hashes; parameter_set_id; model revisions; typed report JSON; report hash |
| evidence_artifacts | artifact_id PK; exact hash; opaque ref; MIME type; size; origin; access scope |
| audit_entries | entry_id PK; previous_entry_sha256; entry_sha256; typed entry JSON; sequence |
| jobs | job_id PK; generation; type; status; typed request/result JSON; error code |
| claim_references/reviews | reference_id/review_id PK; snapshot refs/hashes; reviewer; timestamps; campaign_id |
| geo_baseline_buckets | (origin,collector_scope,h3_resolution,h3_index,hour_utc) PK; count; collection_coverage |

Use TEXT containing validated JSON in SQLite; do not paste PostgreSQL JSONB DDL into SQLite. In-memory and durable adapters obey identical typed contracts. Duplicate ingestion is idempotent; evidence identity never depends on campaign membership.

Bundle format is ZIP containing dossier.json, report.html, report.pdf, stix.json, manifest.json, and authorized evidence artifacts/derivatives. A format-specific export still includes a manifest and disclaimer in its downloadable ZIP. Verify exact raw bytes, canonical event serialization, media bytes, report artifacts, and audit links before export; mismatch fails the job with EVIDENCE_INTEGRITY_MISMATCH. Unavailable evidence is listed as unavailable, never as verified.

Redaction applies consistently to all rendered text, graph labels, timelines, STIX, and embedded metadata. Default masks ORGANIC_USER and UNCLASSIFIED participants. Raw originals stay in restricted storage and are omitted from a redacted bundle; hash and label any sanitized copies as REDACTED_DERIVATIVE with original hash linkage. Redaction is a configurable privacy aid, not a legal compliance guarantee.

STIX 2.1 is validated with the stix2 library. Use observed-data / grouping / note / relationship objects for observations; do not invent threat-actor attribution or malicious indicators from heuristic scores. Preserve algorithm version, collection window, claim status, uncertainty, and synthetic origin in namespaced extensions/custom properties.
