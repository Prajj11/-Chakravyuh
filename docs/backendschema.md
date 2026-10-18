# Backend Data Models, Database Schemas & API Contracts: Project Chakravyuh

**Project Name:** Chakravyuh — Social Media Coordinated Disinformation Detection System  
**Document Version:** 1.0.0  
**Last Updated:** October 18, 2026  
**Schema Standard:** Pydantic v2 (`backend/app/schemas/models.py`), PostgreSQL/SQLite Relational, Neo4j/NetworkX Property Graph, Qdrant Vector Payload, STIX 2.1 JSON.

---

## 1. Enumerations & Domain Constants

```python
from enum import Enum

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
    ORIGINATOR = "ORIGINATOR"               # Crimson (#EF4444) - "Patient Zero"
    BOT_AMPLIFIER = "BOT_AMPLIFIER"         # Amber (#F59E0B) - Synchronized Swarm
    BRIDGE_INFLUENCER = "BRIDGE_INFLUENCER" # Purple (#A855F7) - Cross-community bridge
    ORGANIC_USER = "ORGANIC_USER"           # Teal (#10B981) - Normal participant

class ThreatLevel(str, Enum):
    LOW = "LOW"             # CTI 0 - 39 (Organic)
    MEDIUM = "MEDIUM"       # CTI 40 - 69 (Watchlist)
    HIGH = "HIGH"           # CTI 70 - 84 (Coordinated Campaign)
    CRITICAL = "CRITICAL"   # CTI 85 - 100 (Early Warning Alert)

class HarmCategory(str, Enum):
    COMMUNAL_INCITEMENT = "COMMUNAL_INCITEMENT"
    ELECTORAL_MANIPULATION = "ELECTORAL_MANIPULATION"
    PUBLIC_PANIC = "PUBLIC_PANIC"
    INSTITUTIONAL_DISCREDIT = "INSTITUTIONAL_DISCREDIT"
    BENIGN = "BENIGN"
```

---

## 2. Core Pydantic v2 Data Models (`backend/app/schemas/models.py`)

### 2.1 Layer 1: Ingestion & Canonical Event Models
```python
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class MediaAttachment(BaseModel):
    media_id: str
    media_type: str = Field(..., pattern="^(image|video|audio)$")
    url: str
    phash: str = Field(..., description="64-bit perceptual hash hex string")
    sha256_hash: str

class AccountProfile(BaseModel):
    account_id: str
    handle: str
    display_name: str
    created_at: datetime
    followers_count: int = Field(ge=0)
    following_count: int = Field(ge=0)
    profile_location: Optional[str] = None
    is_verified: bool = False

class GeospatialContext(BaseModel):
    source_lat: Optional[float] = None
    source_lon: Optional[float] = None
    source_region_name: str
    source_h3_index: str
    target_region_name: Optional[str] = None
    target_h3_index: Optional[str] = None
    is_geo_mismatch: bool = False

class UnifiedSocialEvent(BaseModel):
    event_id: str
    platform: PlatformType
    timestamp_utc: datetime
    sha256_hash: str = Field(..., description="Immutable chain-of-custody signature")
    account: AccountProfile
    text: str
    language: str = "en"
    hashtags: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    media_attachments: List[MediaAttachment] = Field(default_factory=list)
    interaction_type: InteractionType = InteractionType.ORIGINAL_POST
    parent_event_id: Optional[str] = None
    target_account_id: Optional[str] = None
    geospatial: GeospatialContext
    narrative_cluster_id: Optional[str] = None
```

### 2.2 Layers 3, 4, 5 & 6: Analytical Enrichment Models
```python
class ForensicMediaReport(BaseModel):
    media_id: str
    media_type: str
    phash: str
    duplicate_matches_count: int = Field(ge=0)
    manipulation_confidence: float = Field(ge=0.0, le=100.0)
    ela_anomaly_score: float = Field(ge=0.0, le=100.0)
    deepfake_visual_score: float = Field(ge=0.0, le=100.0)
    audio_sync_drift_ms: Optional[float] = None
    c2pa_status: str = Field(..., description="VERIFIED_CAMERA | STRIPPED_METADATA | SYNTHETIC_AI_SIGNATURE")
    heatmap_Regions: List[Dict[str, float]] = Field(
        default_factory=list,
        description="Bounding boxes [{x, y, w, h, intensity, label}] for UI overlay"
    )
    evidence_reasons: List[str] = Field(..., min_length=1)

class GraphNode(BaseModel):
    id: str = Field(..., description="Matches account_id")
    handle: str
    role: AccountRole
    bot_probability_score: float = Field(ge=0.0, le=100.0)
    sync_score: float = Field(ge=0.0, le=1.0)
    Sync_latency_sec: float = Field(ge=0.0, description="Mean time delta from seed post")
    posts_in_campaign: int = Field(ge=1)
    community_id: int
    betweenness_centrality: float = Field(ge=0.0)
    out_degree: int = Field(ge=0)
    region: str
    account_created_at: datetime
    feature_contributions: Dict[str, float] = Field(
        ..., description="SHAP-style feature weights summing to bot score"
    )
    evidence_reasons: List[str] = Field(..., min_length=1)

class GraphEdge(BaseModel):
    source: str
    target: str
    interaction_type: str = Field(..., description="CO_POST_SYNC | REPOST_CASCADE | BRIDGE_TRANSFER | ORGANIC_REPLY")
    sync_weight: float = Field(ge=0.0, le=1.0)
    time_delta_sec: float = Field(ge=0.0)

class GeoHexAnomaly(BaseModel):
    h3_index: str
    region_name: str
    latitude: float
    longitude: float
    current_velocity_1hr: int
    baseline_mean_1hr: float
    z_score: float
    geospatial_mismatch_ratio: float = Field(ge=0.0, le=1.0)
    is_astroturfing_alert: bool
    top_source_origins: List[Dict[str, object]] = Field(
        default_factory=list,
        description="List of [{source_region, source_h3, source_lat, source_lon, post_count}]"
    )
```

### 2.3 Layer 7: Campaign Threat Index (CTI), Timeline & Evidence Dossier Models
```python
class TimelineBucket(BaseModel):
    timestamp_label: str
    coordinated_volume: int
    organic_volume: int
    burst_intensity_score: float

class CampaignThreatBreakdown(BaseModel):
    cti_score: float = Field(ge=0.0, le=100.0)
    threat_level: ThreatLevel
    sync_component: float = Field(ge=0.0, le=100.0)
    bot_density_component: float = Field(ge=0.0, le=100.0)
    media_forensics_component: float = Field(ge=0.0, le=100.0)
    geo_anomaly_component: float = Field(ge=0.0, le=100.0)
    harm_severity_component: float = Field(ge=0.0, le=100.0)
    evidence_reasons: List[str] = Field(..., min_length=1)

class NarrativeCampaignSummary(BaseModel):
    campaign_id: str
    title: str
    primary_narrative_claim: str
    languages: List[str]
    harm_category: HarmCategory
    first_detected_utc: datetime
    last_updated_utc: datetime
    total_posts: int
    total_accounts: int
    bot_accounts_count: int
    originator_handle: str
    cti_assessment: CampaignThreatBreakdown
    has_manipulated_media: bool
    has_geo_astroturfing: bool

class NarrativeCampaignDetail(NarrativeCampaignSummary):
    sample_posts: List[UnifiedSocialEvent]
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    timeline: List[TimelineBucket]
    geo_anomalies: List[GeoHexAnomaly]
    media_reports: List[ForensicMediaReport]
```

---

## 3. Polyglot Storage Schemas

### 3.1 Relational Schema (PostgreSQL / SQLite)
```sql
CREATE TABLE narrative_campaigns (
    campaign_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    primary_narrative_claim TEXT NOT NULL,
    harm_category VARCHAR(64) NOT NULL,
    cti_score NUMERIC(5,2) NOT NULL,
    threat_level VARCHAR(32) NOT NULL,
    originator_account_id VARCHAR(64),
    first_detected_utc TIMESTAMP NOT NULL,
    last_updated_utc TIMESTAMP NOT NULL,
    evidence_json JSONB NOT NULL
);

CREATE TABLE social_events (
    event_id VARCHAR(64) PRIMARY KEY,
    campaign_id VARCHAR(64) REFERENCES narrative_campaigns(campaign_id),
    platform VARCHAR(32) NOT NULL,
    account_id VARCHAR(64) NOT NULL,
    handle VARCHAR(128) NOT NULL,
    timestamp_utc TIMESTAMP NOT NULL,
    text TEXT NOT NULL,
    language VARCHAR(16) NOT NULL,
    sha256_hash CHAR(64) NOT NULL,
    source_h3 VARCHAR(20) NOT NULL,
    target_h3 VARCHAR(20),
    is_geo_mismatch BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_events_campaign_time ON social_events(campaign_id, timestamp_utc);
CREATE INDEX idx_events_target_h3 ON social_events(target_h3);
```

### 3.2 Graph Schema (Neo4j Cypher / NetworkX Attributes)
- **Node Label:** `(:Account {id, handle, role, bot_score, sync_score, community_id, region})`
- **Directed Relationships:**
  - `(:Account)-[:CO_POSTED_WITH {sync_weight: 0.94, delta_sec: 8.2, campaign_id: "cmp_01"}]->(:Account)`
  - `(:Account)-[:AMPLIFIED {interaction_type: "repost", timestamp_utc: "..."}]->(:Account)`
  - `(:Account)-[:BRIDGED_TO {betweenness: 0.42}]->(:Account)`

### 3.3 Vector Collection Schema (Qdrant)
- **Collection Name:** `chakravyuh_narrative_embeddings`
- **Vector Params:** `size = 768` (or `384` for lightweight MiniLM), `distance = Distance.COSINE`
- **Payload Indexed Fields:** `campaign_id` (keyword), `timestamp_epoch` (integer), `language` (keyword), `harm_category` (keyword).

---

## 4. FastAPI REST & WebSocket Contract Specification

| Method | Endpoint | Description | Response Model |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | System readiness, active layer status & event count | `HealthStatusResponse` |
| `GET` | `/api/v1/campaigns` | List all active narrative campaigns sorted by CTI descending | `List[NarrativeCampaignSummary]` |
| `GET` | `/api/v1/campaigns/{campaign_id}` | Full campaign workbench payload (graph, timeline, geo, media) | `NarrativeCampaignDetail` |
| `POST`| `/api/v1/simulate/scenario` | Switch or replay deterministic scenario (`electoral_deepfake`, `geo_astroturf`, `organic_baseline`) | `NarrativeCampaignDetail` |
| `POST`| `/api/v1/events/inject` | Inject a live custom post/media event through all 7 Chakravyuh layers | `UnifiedSocialEventEnriched` |
| `POST`| `/api/v1/forensics/verify-media`| Run on-demand pHash, ELA, and Deepfake inspection on media payload | `ForensicMediaReport` |
| `GET` | `/api/v1/campaigns/{campaign_id}/export` | Generate court-ready Evidence Dossier + STIX 2.1 threat bundle (`?redact_pii=true`) | `EvidenceDossierBundle` |
| `WS`  | `/ws/stream` | Real-time push stream of new ingested events and CTI Early Warning Alerts | `WebSocketStreamMessage` |
