from io import BytesIO

import h3
from PIL import Image

from app.config import Parameters
from app.coordination.engine import CoordinationEngine
from app.geo_engine.engine import GeoEngine, topic_family
from app.graph_engine.engine import GraphEngine
from app.ingestion.contracts import SourceEvent
from app.ingestion.service import IngestionService
from app.ingestion.simulator import (
    SCENARIO_IDS,
    ingest_scenario,
    load_coverage,
    load_history,
    media_bytes,
)
from app.media_forensics.engine import MediaEngine
from app.repositories.evidence import EvidenceRepository
from app.repositories.state import GeoBaselineBucket, StatePartition
from app.schemas.models import AccountRole, AnalysisStatus, DataOrigin


def test_graph_seed_precedence_and_timeline_partition(repository: EvidenceRepository) -> None:
    events = list(ingest_scenario(SCENARIO_IDS[0], IngestionService(repository), scope="test"))
    coordination = CoordinationEngine(Parameters()).analyze(events, similarity=lambda _a, _b: 1)
    graph = GraphEngine(Parameters()).build(events, coordination)
    earliest = min(
        events, key=lambda event: (event.timestamp_utc, event.account.account_id)
    ).account.account_id
    assert (
        next(node for node in graph.nodes if node.id == earliest).role
        == AccountRole.EARLIEST_OBSERVED_SEED
    )
    assert sum(
        bucket.coordinated_volume + bucket.low_indicator_volume + bucket.unclassified_volume
        for bucket in graph.timeline
    ) == len(events)
    assert graph.nodes == GraphEngine(Parameters()).build(events, coordination).nodes
    assert all(edge.source != edge.target for edge in graph.edges)


def test_empty_single_graph_and_unresolved_parents(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    engine = GraphEngine(Parameters())
    coordination = CoordinationEngine(Parameters())
    assert engine.build([], coordination.analyze([], similarity=lambda _a, _b: 0)).nodes == []
    event = IngestionService(repository).ingest(
        source.model_copy(update={"parent_event_id": "unknown"}), scope="test"
    )
    graph = engine.build([event], coordination.analyze([event], similarity=lambda _a, _b: 0))
    assert len(graph.nodes) == 1 and graph.nodes[0].betweenness_centrality == 0
    assert graph.edges == []


def test_real_media_hash_ela_heatmap_and_unsupported(repository: EvidenceRepository) -> None:
    with repository.transaction() as db:
        artifact, digest = repository.put_artifact(
            db, media_bytes("spliced"), "MEDIA", "image/jpeg", DataOrigin.USER_INJECTED, "test"
        )
    report = MediaEngine(repository, "test").verify(artifact)
    assert report.analysis_status == AnalysisStatus.AVAILABLE
    assert report.phash and len(report.phash) == 16
    assert report.manipulation_indicator_score == report.ela_anomaly_score
    assert report.deepfake_visual_score is None and report.exif_present is False
    assert report.duplicate_matches_count == 0
    assert report.heatmap_artifact_ref is not None
    heatmap, _, _ = repository.artifact(report.heatmap_artifact_ref, "test")
    with Image.open(BytesIO(heatmap)) as image:
        assert image.size == (640, 400)
    with repository.transaction() as db:
        video, _ = repository.put_artifact(
            db,
            b"retained-video-placeholder",
            "MEDIA",
            "video/mp4",
            DataOrigin.USER_INJECTED,
            "test",
        )
        corrupt, _ = repository.put_artifact(
            db, b"broken-image", "MEDIA", "image/png", DataOrigin.USER_INJECTED, "test"
        )
    unsupported = MediaEngine(repository, "test").verify(video)
    assert (
        unsupported.analysis_status == AnalysisStatus.UNSUPPORTED
        and unsupported.manipulation_indicator_score is None
    )
    assert MediaEngine(repository, "test").verify(corrupt).analysis_status == AnalysisStatus.FAILED
    assert repository.verify("test")["artifacts"] >= 4


def test_geo_missing_denominator_and_baseline_scope(repository: EvidenceRepository) -> None:
    p = Parameters()
    events = list(ingest_scenario(SCENARIO_IDS[1], IngestionService(repository), scope="test"))
    partition = StatePartition(
        data_origin=DataOrigin.SYNTHETIC_REPLAY, collector_scope=load_coverage()[0].collector_scope
    )
    engine = GeoEngine(p)
    reports = engine.analyze(
        events, all_events=events, partition=partition, sync_score=0.65, baselines=[]
    )
    report = reports[0]
    assert report.z_score is None and report.baseline_status == AnalysisStatus.INSUFFICIENT_DATA
    assert report.is_astroturfing_alert
    assert 0.7 <= report.geospatial_mismatch_ratio <= 0.9
    assert not engine.analyze(
        events, all_events=events, partition=partition, sync_score=0.649, baselines=[]
    )[0].is_astroturfing_alert
    history = load_history()
    buckets = [
        GeoBaselineBucket(
            topic_family_id="civic-participation",
            h3_index=hour.h3_index,
            hour_utc=hour.hour_utc,
            collection_coverage=hour.collection_coverage,
            count=sum(
                event.timestamp_utc.replace(minute=0, second=0) == hour.hour_utc
                for event in history
            ),
        )
        for hour in load_coverage()
    ]
    with_history = engine.analyze(
        events, all_events=events, partition=partition, sync_score=0.65, baselines=buckets
    )[0]
    assert with_history.baseline_bucket_count == 240 and with_history.z_score is not None
    assert (
        engine.analyze(
            events, all_events=events, partition=partition, sync_score=0.65, baselines=buckets[:167]
        )[0].z_score
        is None
    )
    assert (
        engine.analyze(
            events,
            all_events=events,
            partition=partition,
            sync_score=0.65,
            baselines=[
                bucket.model_copy(update={"topic_family_id": "unrelated"}) for bucket in buckets
            ],
        )[0].z_score
        is None
    )
    assert topic_family("unrelated unknown subject") is None


def test_geo_unknown_sources_never_use_target_as_source(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    from app.schemas.models import GeospatialContext

    target = h3.latlng_to_cell(26.8467, 80.9462, 5)
    event = IngestionService(repository).ingest(
        source.model_copy(
            update={
                "geospatial": GeospatialContext(
                    target_region_name="Lucknow", target_h3_index=target
                )
            }
        ),
        scope="test",
    )
    partition = StatePartition(
        data_origin=event.data_origin, collector_scope=source.collector_scope
    )
    report = GeoEngine(Parameters()).analyze(
        [event], all_events=[event], partition=partition, sync_score=1, baselines=[]
    )[0]
    assert report.geospatial_mismatch_ratio is None
    assert report.source_location_coverage_ratio == 0 and not report.is_astroturfing_alert
