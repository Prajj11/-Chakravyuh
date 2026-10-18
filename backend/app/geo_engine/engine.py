"""H3 source/subject separation and same-partition observed hourly baselines."""

import json
import statistics
from collections import Counter
from collections.abc import Sequence
from datetime import timedelta

import h3

from app.config import Parameters
from app.evidence.canonical import canonical_bytes, sha256
from app.ingestion.simulator import fixture_root
from app.nlp_engine.engine import normalize_text
from app.repositories.state import GeoBaselineBucket, StatePartition
from app.schemas.models import (
    AnalysisStatus,
    ComputationMode,
    GeoHexAnomaly,
    GeospatialContext,
    LocationConfidence,
    SourceOrigin,
    UnifiedSocialEvent,
)

TOPIC_DICTIONARY = {
    "version": "topic-v1",
    "civic-participation": [
        "election",
        "voting",
        "polling",
        "relief",
        "supplies",
        "community participation",
        "मतदान",
        "राहत",
    ],
}


def topic_family(text: str) -> str | None:
    normalized = normalize_text(text)
    for keyword in TOPIC_DICTIONARY["civic-participation"]:
        if keyword in normalized:
            return "civic-participation"
    return None


class GeoEngine:
    def __init__(self, parameters: Parameters) -> None:
        self.p = parameters
        self.places = json.loads(
            (fixture_root() / "registries" / "gazetteer.json").read_text(encoding="utf-8")
        )

    def resolve(self, event: UnifiedSocialEvent) -> GeospatialContext:
        body = event.geospatial.model_dump()
        if (
            event.geospatial.source_location_confidence == LocationConfidence.UNAVAILABLE
            and event.account.profile_location
        ):
            matches = [
                place
                for place in self.places
                if place["name"].casefold() == event.account.profile_location.strip().casefold()
            ]
            if len(matches) == 1:
                place = matches[0]
                body.update(
                    source_lat=place["lat"],
                    source_lon=place["lon"],
                    source_h3_index=place["h3_index"],
                    source_region_name=place["name"],
                    source_location_confidence=LocationConfidence.PROFILE_DECLARED,
                )
        if event.geospatial.target_h3_index is None:
            matches = [
                place
                for place in self.places
                if place["name"].casefold()
                == (event.geospatial.target_region_name or "").casefold()
                or place["name"].casefold() in normalize_text(event.text)
            ]
            if len(matches) == 1:
                body.update(
                    target_region_name=matches[0]["name"], target_h3_index=matches[0]["h3_index"]
                )
        return GeospatialContext.model_validate(body)

    def analyze(
        self,
        events: Sequence[UnifiedSocialEvent],
        *,
        all_events: Sequence[UnifiedSocialEvent],
        partition: StatePartition,
        sync_score: float | None,
        baselines: Sequence[GeoBaselineBucket],
    ) -> list[GeoHexAnomaly]:
        if not events:
            return []
        p = self.p
        if any(event.data_origin != partition.data_origin for event in [*events, *all_events]):
            raise ValueError("Geo input origins must match their partition")
        watermark = max(event.timestamp_utc for event in all_events or events)
        cutoff = watermark - timedelta(seconds=p.GEO_TRAILING_WINDOW_SEC)
        contexts = {event.event_id: self.resolve(event) for event in [*events, *all_events]}
        families = {family for event in events if (family := topic_family(event.text)) is not None}
        family = next(iter(families)) if len(families) == 1 else None
        cells = sorted(
            {
                target_cell
                for event in events
                if (target_cell := contexts[event.event_id].target_h3_index) is not None
            }
        )
        reports = []
        for cell in cells:
            selected = [
                event
                for event in events
                if cutoff < event.timestamp_utc <= watermark
                and contexts[event.event_id].target_h3_index == cell
            ]
            known = [event for event in selected if contexts[event.event_id].source_h3_index]
            coverage = len(known) / len(selected) if selected else 0
            neighbourhood = set(h3.grid_disk(cell, p.GEO_GRID_RADIUS))
            external = sum(
                contexts[event.event_id].source_h3_index not in neighbourhood for event in known
            )
            mismatch = external / len(known) if known else None
            accounts = len({event.account.account_id for event in known})
            gates = {
                "mismatch_ratio": mismatch is not None
                and mismatch >= p.ASTROTURFING_MISMATCH_RATIO,
                "source_coverage": coverage >= p.GEO_MIN_SOURCE_COVERAGE,
                "known_source_posts": len(known) >= p.GEO_MIN_KNOWN_SOURCE_POSTS,
                "known_source_accounts": accounts >= p.GEO_MIN_KNOWN_SOURCE_ACCOUNTS,
                "coordination": sync_score is not None and sync_score >= p.BOT_SYNC_SCORE_CUTOFF,
            }
            current = sum(
                cutoff < event.timestamp_utc <= watermark
                and contexts[event.event_id].target_h3_index == cell
                and family is not None
                and topic_family(event.text) == family
                for event in all_events
            )
            history = [
                bucket
                for bucket in baselines
                if bucket.h3_index == cell
                and bucket.topic_family_id == family
                and bucket.collection_coverage >= p.GEO_MIN_COLLECTION_COVERAGE
                and watermark - timedelta(days=p.GEO_BASELINE_LOOKBACK_DAYS) <= bucket.hour_utc
                and bucket.hour_utc + timedelta(hours=1) <= cutoff
            ]
            sufficient = len(history) >= p.GEO_BASELINE_MIN_HOURLY_BUCKETS
            mean = statistics.mean(bucket.count for bucket in history) if sufficient else None
            std = statistics.stdev(bucket.count for bucket in history) if sufficient else None
            z = (current - mean) / max(std, 1) if mean is not None and std is not None else None
            origin_counts: Counter[tuple[str, LocationConfidence]] = Counter()
            for event in known:
                context = contexts[event.event_id]
                if context.source_h3_index is not None:
                    origin_counts[
                        (context.source_h3_index, context.source_location_confidence)
                    ] += 1
            origins = []
            for (source_cell, confidence), count in sorted(
                origin_counts.items(), key=lambda item: (-item[1], item[0])
            ):
                latitude, longitude = h3.cell_to_latlng(source_cell)
                origins.append(
                    SourceOrigin(
                        source_h3_index=source_cell,
                        source_region=next(
                            (
                                contexts[event.event_id].source_region_name
                                for event in known
                                if contexts[event.event_id].source_h3_index == source_cell
                            ),
                            None,
                        ),
                        source_location_confidence=confidence,
                        latitude=latitude,
                        longitude=longitude,
                        post_count=count,
                    )
                )
            latitude, longitude = h3.cell_to_latlng(cell)
            reports.append(
                GeoHexAnomaly(
                    computation_mode=ComputationMode.COMPUTED_PIPELINE,
                    analysis_status=AnalysisStatus.AVAILABLE
                    if known or sufficient
                    else AnalysisStatus.INSUFFICIENT_DATA,
                    parameter_set_id=p.parameter_set_id,
                    coverage_ratio=coverage,
                    missing_signals=([] if known else ["known_author_source"])
                    + ([] if sufficient else ["same_scope_hourly_baseline"]),
                    evidence_reasons=[
                        "Failed mismatch gates: "
                        + ", ".join(key for key, passed in gates.items() if not passed),
                        "Declared profile locations are declarations, not physical-location proof.",
                        f"Baseline topic dictionary: {TOPIC_DICTIONARY['version']}; "
                        f"topic={family}.",
                    ],
                    h3_index=cell,
                    baseline_scope_id=sha256(
                        canonical_bytes([partition, cell, family, TOPIC_DICTIONARY])
                    ),
                    window_end_utc=watermark,
                    region_name=next(
                        (
                            contexts[event.event_id].target_region_name
                            for event in events
                            if contexts[event.event_id].target_h3_index == cell
                        ),
                        None,
                    ),
                    latitude=latitude,
                    longitude=longitude,
                    current_velocity_1hr=current,
                    target_campaign_posts_1hr=len(selected),
                    baseline_mean_1hr=mean,
                    baseline_std_1hr=std,
                    baseline_bucket_count=len(history),
                    baseline_status=AnalysisStatus.AVAILABLE
                    if sufficient
                    else AnalysisStatus.INSUFFICIENT_DATA,
                    baseline_data_origin=partition.data_origin if sufficient else None,
                    z_score=z,
                    source_location_coverage_ratio=coverage,
                    known_source_posts=len(known),
                    known_source_accounts=accounts,
                    geospatial_mismatch_ratio=mismatch,
                    coordination_sync_score=sync_score,
                    is_astroturfing_alert=all(gates.values()),
                    top_source_origins=origins,
                )
            )
        return reports
