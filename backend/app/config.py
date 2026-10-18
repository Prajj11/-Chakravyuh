"""Central versioned analytical defaults, independent of machine/session configuration."""

from pathlib import Path
from typing import Literal, Never, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.evidence.canonical import canonical_bytes, sha256
from app.schemas.models import ContractModel


class FrozenWeights(dict[str, float]):
    """A serializable read-only mapping; parameters cannot drift after registration."""

    def _immutable(self, *args: object, **kwargs: object) -> Never:
        raise TypeError("Parameter weights are immutable; create a new parameter set")

    __setitem__ = _immutable
    __delitem__ = _immutable
    update = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    __ior__ = _immutable


class Parameters(ContractModel):
    PARAMETER_VERSION: str = "2.1.0.1"
    SYNC_BUCKET_SEC: int = 60
    ACCOUNT_TOP_SYNC_PEERS: int = 5
    COORDINATION_MIN_POSTS: int = 10
    BURST_MIN_COMPLETE_BINS: int = 10
    BURST_MIN_EVENTS: int = 20
    CREATION_BATCH_WINDOW_HOURS: float = 48
    CREATION_BATCH_MIN_KNOWN_PEERS: int = 3
    CREATION_BATCH_DENSITY_DENOMINATOR: float = 10
    POSTING_RATE_BURST_SCALE: float = 9
    HANDLE_TRAILING_DIGIT_CAP: int = 6
    HARM_MIN_LANGUAGE_COVERAGE: float = 0.30
    PHASH_MAX_DISTANCE: int = 10
    LOUVAIN_RESOLUTION: float = 1
    BRIDGE_CENTRALITY_PERCENTILE: float = 85
    BRIDGE_MIN_INTERACTION_EDGES: int = 2
    ELA_JPEG_QUALITY: int = 90
    ELA_DISPLAY_SCALE: float = 15
    ELA_SCORE_SCALE: float = 10
    ELA_REGION_THRESHOLD: float = 15
    ELA_MIN_COMPONENT_PIXELS: int = 16
    GEO_TRAILING_WINDOW_SEC: int = 3600
    GEO_GRID_RADIUS: int = 2
    GEO_MIN_COLLECTION_COVERAGE: float = 0.90
    GEO_Z_COMPONENT_SCALE: float = 6
    CTI_BOT_MIN_SCORED_AUTHORS: int = 3
    CTI_MEDIUM_THRESHOLD: float = 40
    CTI_HIGH_THRESHOLD: float = 60
    MEDIA_INDICATOR_THRESHOLD: float = 50
    SEMANTIC_CLUSTER_SIMILARITY: float = Field(default=0.85, ge=0, le=1)
    NARRATIVE_WINDOW_HOURS: int = Field(default=24, gt=0)
    TEMPORAL_CO_POST_WINDOW_SEC: float = Field(default=60, gt=0)
    TEMPORAL_DECAY_TAU_SEC: float = Field(default=20, gt=0)
    SYNC_MIN_DISTINCT_BUCKETS: int = Field(default=2, ge=2)
    ANALYSIS_MIN_OBSERVATION_SEC: int = Field(default=180, gt=0)
    ANALYSIS_MIN_ACCOUNT_POSTS: int = Field(default=3, ge=1)
    COORDINATION_MIN_AUTHORS: int = Field(default=3, ge=3)
    BOT_PROBABILITY_HIGH_CUTOFF: float = Field(default=70, ge=0, le=100)
    BOT_SYNC_SCORE_CUTOFF: float = Field(default=0.65, ge=0, le=1)
    ORGANIC_BOT_MAX_EXCLUSIVE: float = Field(default=50, ge=0, le=100)
    ORGANIC_SYNC_MAX_EXCLUSIVE: float = Field(default=0.45, ge=0, le=1)
    BOT_MIN_FEATURE_COVERAGE: float = Field(default=0.30, gt=0, le=1)
    ORGANIC_MIN_FEATURE_COVERAGE: float = Field(default=0.60, gt=0, le=1)
    GEO_H3_RESOLUTION: Literal[5] = 5
    GEO_Z_SCORE_SPIKE_THRESHOLD: float = Field(default=3, gt=0)
    GEO_BASELINE_LOOKBACK_DAYS: int = Field(default=30, gt=0)
    GEO_BASELINE_MIN_HOURLY_BUCKETS: int = Field(default=168, ge=2)
    GEO_MIN_SOURCE_COVERAGE: float = Field(default=0.30, gt=0, le=1)
    GEO_MIN_KNOWN_SOURCE_POSTS: int = Field(default=10, ge=1)
    GEO_MIN_KNOWN_SOURCE_ACCOUNTS: int = Field(default=5, ge=1)
    ASTROTURFING_MISMATCH_RATIO: float = Field(default=0.60, ge=0, le=1)
    CTI_MIN_COMPONENT_COVERAGE: float = Field(default=0.60, gt=0, le=1)
    CTI_MIN_SCORED_POST_COVERAGE: float = Field(default=0.30, gt=0, le=1)
    CTI_CRITICAL_ALERT_THRESHOLD: float = Field(default=75, ge=0, le=100)
    ALERT_MIN_CAMPAIGN_POSTS: int = Field(default=10, ge=1)
    ALERT_MIN_CAMPAIGN_AUTHORS: int = Field(default=5, ge=1)
    ALERT_COOLDOWN_SEC: int = Field(default=300, ge=0)
    ALERT_REARM_BELOW: float = Field(default=70, ge=0, le=100)
    ALERT_REARM_SEC: int = Field(default=120, ge=0)
    CLAIM_CANDIDATE_SIMILARITY: float = Field(default=0.85, ge=0, le=1)
    RANDOM_SEED: int = 42
    BOT_FEATURE_WEIGHTS: dict[str, float] = Field(
        default_factory=lambda: {
            "sync_tightness": 0.35,
            "creation_batch_density": 0.25,
            "amplification_ratio": 0.20,
            "posting_rate_burst": 0.10,
            "handle_entropy": 0.10,
        }
    )
    CTI_WEIGHTS: dict[str, float] = Field(
        default_factory=lambda: {
            "sync": 0.30,
            "bot_density": 0.25,
            "media_forensics": 0.20,
            "geo_anomaly": 0.15,
            "harm_severity": 0.10,
        }
    )

    @model_validator(mode="after")
    def valid_weights(self) -> Self:
        expected_bot = {
            "sync_tightness",
            "creation_batch_density",
            "amplification_ratio",
            "posting_rate_burst",
            "handle_entropy",
        }
        expected_cti = {"sync", "bot_density", "media_forensics", "geo_anomaly", "harm_severity"}
        if set(self.BOT_FEATURE_WEIGHTS) != expected_bot or set(self.CTI_WEIGHTS) != expected_cti:
            raise ValueError("Analytical weight keys must match the versioned feature definitions")
        for weights in (self.BOT_FEATURE_WEIGHTS, self.CTI_WEIGHTS):
            if (
                any(not 0 <= w <= 1 for w in weights.values())
                or abs(sum(weights.values()) - 1) > 1e-9
            ):
                raise ValueError("Analytical weights must be finite, positive and sum to one")
        object.__setattr__(self, "BOT_FEATURE_WEIGHTS", FrozenWeights(self.BOT_FEATURE_WEIGHTS))
        object.__setattr__(self, "CTI_WEIGHTS", FrozenWeights(self.CTI_WEIGHTS))
        return self

    @property
    def parameter_set_id(self) -> str:
        return sha256(canonical_bytes(self))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CHAKRAVYUH_", env_file=".env", extra="forbid")
    data_dir: Path = Path(__file__).resolve().parents[2] / ".runtime"
    frontend_origin: str = "http://127.0.0.1:3000"
    session_token: SecretStr | None = None
    upload_limit_bytes: int = Field(default=25 * 1024 * 1024, gt=0, le=25 * 1024 * 1024)
    image_max_pixels: int = Field(default=24_000_000, gt=0)
    cached_model_dir: Path | None = None

    @model_validator(mode="after")
    def secure_token(self) -> Self:
        origin = urlsplit(self.frontend_origin)
        if (
            origin.scheme != "http"
            or origin.hostname not in {"localhost", "127.0.0.1"}
            or origin.path
            or origin.query
            or origin.fragment
            or origin.username
            or origin.password
        ):
            raise ValueError("Frontend origin must be an exact loopback HTTP origin")
        if origin.port is not None and not 1 <= origin.port <= 65535:
            raise ValueError("Invalid frontend origin port")
        if self.session_token is not None and len(self.session_token.get_secret_value()) < 32:
            raise ValueError("Local session token must have at least 32 characters")
        return self
