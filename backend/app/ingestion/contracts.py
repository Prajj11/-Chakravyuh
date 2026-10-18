"""Trusted connector boundary; public API clients cannot set provenance fields."""

from typing import Literal

from pydantic import AwareDatetime, Field

from app.schemas.models import (
    SHA256,
    AccountProfile,
    ContractModel,
    DataOrigin,
    GeospatialContext,
    InteractionType,
    MediaAttachment,
    PlatformType,
)


class SourceEvent(ContractModel):
    source_event_key: str = Field(min_length=1)
    platform: PlatformType
    data_origin: DataOrigin
    collector_id: str = Field(min_length=1)
    collector_scope: str = Field(min_length=1)
    source_url: str | None = None
    timestamp_utc: AwareDatetime
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


class CaptureManifest(ContractModel):
    collector_id: str
    collector_scope: str
    source_event_key: str
    source_url: str | None
    content_type: str
    capture_format: Literal["HTTP_ENTITY_BYTES", "CANONICAL_JSON_V1"]
    collection_timestamp_utc: AwareDatetime
    raw_payload_sha256: SHA256
    raw_payload_ref: str
    data_origin: DataOrigin
    source_pointer: str | None = None
