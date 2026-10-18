"""Shared observed-input pipeline for replay, user injection and optional public adapters."""

from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from functools import partial
from uuid import uuid4

import h3
import numpy as np

from app.coordination.engine import CoordinationEngine
from app.evidence.canonical import sha256
from app.geo_engine.engine import GeoEngine, topic_family
from app.graph_engine.engine import GraphEngine
from app.ingestion.contracts import SourceEvent
from app.ingestion.service import IngestionService
from app.ingestion.simulator import fixture_root, load_claim_references, load_coverage, load_history
from app.media_forensics.engine import MediaEngine
from app.nlp_engine.engine import NarrativeEngine, Vector
from app.reporting.cti import AlertState, compute_cti
from app.repositories.state import GeoBaselineBucket, StatePartition, StateRepository
from app.schemas.models import (
    AccountProfile,
    AccountRole,
    CampaignAlert,
    CollectionWindowMetadata,
    DataOrigin,
    EventInjectRequest,
    ForensicMediaReport,
    GeospatialContext,
    LocationConfidence,
    MediaAttachment,
    NarrativeCampaignDetail,
    NarrativeCampaignSummary,
    PlatformType,
    UnifiedSocialEvent,
    UnifiedSocialEventEnriched,
)


class Pipeline:
    def __init__(self, state: StateRepository) -> None:
        self.state = state
        self.repo = state.evidence
        self.p = self.repo.parameters
        self.ingestor = IngestionService(self.repo)
        self.nlp = NarrativeEngine(self.p)
        self.coordination = CoordinationEngine(self.p)
        self.graph = GraphEngine(self.p)
        self.geo = GeoEngine(self.p)
        self.media = MediaEngine(self.repo, state.scope)
        self.alerts: dict[str, AlertState] = {}
        self.media_cache: dict[tuple[str, tuple[str, ...]], ForensicMediaReport] = {}
        for reference in load_claim_references():
            data = (fixture_root() / reference.snapshot_ref).read_bytes()
            with self.repo.transaction() as db:
                ref, _ = self.repo.put_artifact(
                    db, data, "REFERENCE", "text/plain", DataOrigin.SYNTHETIC_REPLAY, state.scope
                )
            state.put_claim_reference(reference.model_copy(update={"snapshot_ref": ref}))

    def history(self, seed: int) -> None:
        history = load_history(seed)
        for source in history:
            self.ingestor.ingest(source, scope=self.state.scope)
        counts = Counter(
            (
                source.timestamp_utc.replace(minute=0, second=0, microsecond=0),
                source.geospatial.target_h3_index,
                topic_family(source.text),
            )
            for source in history
        )
        for hour in load_coverage(seed):
            partition = StatePartition(
                data_origin=DataOrigin.SYNTHETIC_REPLAY, collector_scope=hour.collector_scope
            )
            self.state.put_baseline_bucket(
                partition,
                GeoBaselineBucket(
                    topic_family_id=hour.topic_family_id,
                    h3_index=hour.h3_index,
                    hour_utc=hour.hour_utc,
                    count=counts[(hour.hour_utc, hour.h3_index, hour.topic_family_id)],
                    collection_coverage=hour.collection_coverage,
                ),
            )

    def activate(
        self, source: SourceEvent, partition: StatePartition, generation: int
    ) -> UnifiedSocialEvent:
        with self.state.mutation(partition, generation):
            event = self.ingestor.ingest(source, scope=self.state.scope)
            self.state.record_account(partition, generation, event.event_id)
        return event

    def inject_source(self, request: EventInjectRequest) -> SourceEvent:
        media = []
        for artifact_id in request.media_artifact_ids:
            data, mime, kind = self.repo.artifact(artifact_id, self.state.scope)
            with self.repo._lock:
                origin = self.repo._db.execute(
                    "SELECT origin FROM evidence_artifacts WHERE artifact_id=?", (artifact_id,)
                ).fetchone()[0]
            if kind != "MEDIA" or origin != DataOrigin.USER_INJECTED.value:
                raise ValueError("Injected media must be uploaded in this origin and scope")
            media_type = (
                "image"
                if mime.startswith("image/")
                else "video"
                if mime.startswith("video/")
                else "audio"
            )
            media.append(
                MediaAttachment.model_validate(
                    {
                        "media_id": artifact_id,
                        "media_type": media_type,
                        "sha256_hash": sha256(data),
                        "evidence_ref": artifact_id,
                        "collection_status": "COLLECTED",
                    }
                )
            )
        actor = request.account_id or "custom-" + sha256(request.handle.encode())[:16]
        if actor.startswith("simulator:"):
            actor = actor[len("simulator:") :]
        if ":" in actor:
            raise ValueError("Injection cannot impersonate another platform identity")
        geo = GeospatialContext(
            source_lat=request.source_lat,
            source_lon=request.source_lon,
            source_h3_index=h3.latlng_to_cell(request.source_lat, request.source_lon, 5)
            if request.source_lat is not None
            else None,
            source_location_confidence=LocationConfidence.EXPLICIT_GPS
            if request.source_lat is not None
            else LocationConfidence.UNAVAILABLE,
            target_region_name=request.target_region_name,
        )
        return SourceEvent(
            source_event_key=uuid4().hex,
            platform=PlatformType.SIMULATOR,
            data_origin=DataOrigin.USER_INJECTED,
            collector_id="local-injection-v1",
            collector_scope="injected-v1",
            timestamp_utc=request.timestamp_utc or datetime.now(UTC),
            account=AccountProfile(
                account_id="simulator:" + actor,
                handle=request.handle,
                profile_location=request.profile_location,
            ),
            text=request.text,
            language=request.language,
            media_attachments=tuple(media),
            geospatial=geo,
        )

    def refresh(
        self, partition: StatePartition, generation: int
    ) -> tuple[list[NarrativeCampaignDetail], list[CampaignAlert]]:
        events = self.state.list_events(partition)
        clusters = self.nlp.cluster(events, partition_id=partition.key)
        details = []
        pending_alerts = []
        for cluster in clusters:
            members = [event for event in events if event.event_id in cluster.event_ids]
            vectors = self.nlp.embed([event.text for event in members])
            indices = {event.event_id: index for index, event in enumerate(members)}
            coordination = self.coordination.analyze(
                members,
                similarity=partial(vector_similarity, vectors, indices),
            )
            graph = self.graph.build(members, coordination)
            media_ids = tuple(
                sorted(
                    {
                        media.evidence_ref
                        for event in members
                        for media in event.media_attachments
                        if media.evidence_ref
                    }
                )
            )
            media_reports = []
            for media_id in media_ids:
                self.repo.artifact(media_id, self.state.scope)
                key = (media_id, media_ids)
                if key not in self.media_cache:
                    self.media_cache[key] = self.media.verify(media_id, comparison_ids=media_ids)
                media_reports.append(self.media_cache[key])
            geo = self.geo.analyze(
                members,
                all_events=events,
                partition=partition,
                sync_score=coordination.assessment.sync_score,
                baselines=self.state.list_baseline_buckets(partition),
            )
            harm = self.nlp.harm(members)
            cti = compute_cti(
                self.p,
                members,
                coordination.assessment,
                coordination.bots,
                media_reports,
                geo,
                harm,
            )
            try:
                previous = self.state.get_campaign(cluster.campaign_id)
            except KeyError:
                previous = None
            reviews = self.state.list_claim_reviews(cluster.campaign_id)
            verification = (
                reviews[-1]
                if reviews
                else self.nlp.claim(
                    members[0].text,
                    partition.data_origin,
                    cluster.last_updated_utc,
                    self.state.list_claim_references(),
                )
            )
            seed = next(
                (
                    node.handle
                    for node in graph.nodes
                    if node.role == AccountRole.EARLIEST_OBSERVED_SEED
                ),
                None,
            )
            detail = NarrativeCampaignDetail(
                campaign_id=cluster.campaign_id,
                snapshot_revision=previous.snapshot_revision + 1 if previous else 1,
                title=members[0].text[:100],
                primary_narrative_claim=members[0].text,
                data_origin=partition.data_origin,
                claim_verification=verification,
                collection_window=CollectionWindowMetadata(
                    window_start_utc=cluster.first_detected_utc,
                    window_end_utc=cluster.last_updated_utc,
                    collector_sources=sorted({event.collector_id for event in members}),
                ),
                languages=sorted({event.language for event in members}),
                first_detected_utc=cluster.first_detected_utc,
                last_updated_utc=cluster.last_updated_utc,
                total_posts=len(members),
                total_accounts=len(graph.nodes),
                bot_accounts_count=sum(
                    node.role == AccountRole.BOT_AMPLIFIER for node in graph.nodes
                ),
                earliest_seed_handle=seed,
                coordination_assessment=coordination.assessment,
                cti_assessment=cti,
                has_media_indicators=any(
                    report.manipulation_indicator_score is not None
                    and report.manipulation_indicator_score >= self.p.MEDIA_INDICATOR_THRESHOLD
                    for report in media_reports
                ),
                has_geo_astroturfing=any(report.is_astroturfing_alert for report in geo),
                sample_posts=members,
                nodes=graph.nodes,
                edges=graph.edges,
                timeline=graph.timeline,
                geo_anomalies=geo,
                media_reports=media_reports,
                harm_assessment=harm,
            )
            details.append(detail)
        with self.state.mutation(partition, generation):
            with self.repo.transaction() as db:
                db.execute(
                    "DELETE FROM campaigns WHERE scope=? AND partition_id=? AND generation=?",
                    (self.state.scope, partition.key, generation),
                )
            for detail in details:
                self.repo.record_analysis(
                    detail,
                    [event.canonical_event_sha256 for event in detail.sample_posts],
                    {self.nlp.model_id: self.nlp.revision},
                    partition.data_origin,
                    self.state.scope,
                )
                self.state.put_campaign(partition, generation, detail)
                for event in detail.sample_posts:
                    self.state.add_membership(
                        partition,
                        generation,
                        detail.campaign_id,
                        event.event_id,
                        detail.snapshot_revision,
                    )
                alert_state = self.alerts.setdefault(detail.campaign_id, AlertState())
                if alert_state.observe(detail.cti_assessment, detail.last_updated_utc, self.p):
                    pending_alerts.append(
                        CampaignAlert(
                            campaign_id=detail.campaign_id, assessment=detail.cti_assessment
                        )
                    )
        return details, pending_alerts

    def enriched(
        self,
        event: UnifiedSocialEvent,
        details: Sequence[NarrativeCampaignDetail],
        alerts: Sequence[CampaignAlert],
    ) -> UnifiedSocialEventEnriched:
        detail = next(
            detail
            for detail in details
            if any(post.event_id == event.event_id for post in detail.sample_posts)
        )
        node = next(node for node in detail.nodes if node.id == event.account.account_id)
        return UnifiedSocialEventEnriched(
            event=event,
            assigned_campaign_id=detail.campaign_id,
            bot_assessment=node.bot_assessment,
            sync_assessment=node.sync_assessment,
            updated_campaign_cti=detail.cti_assessment,
            triggered_critical_alert=any(
                alert.campaign_id == detail.campaign_id for alert in alerts
            ),
        )


def summary(detail: NarrativeCampaignDetail) -> NarrativeCampaignSummary:
    return NarrativeCampaignSummary.model_validate(
        {
            key: value
            for key, value in detail.model_dump().items()
            if key in NarrativeCampaignSummary.model_fields
        }
    )


def vector_similarity(
    vectors: Vector, indices: dict[str, int], a: UnifiedSocialEvent, b: UnifiedSocialEvent
) -> float:
    return float(np.clip(np.dot(vectors[indices[a.event_id]], vectors[indices[b.event_id]]), 0, 1))
