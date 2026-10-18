from datetime import timedelta
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from app.config import Parameters
from app.coordination.engine import CoordinationEngine, CoordinationResult, PairMatch, SyncEdge
from app.graph_engine.engine import GraphEngine
from app.ingestion.contracts import SourceEvent
from app.ingestion.service import IngestionService
from app.ingestion.simulator import media_bytes
from app.media_forensics.engine import MediaEngine
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import (
    AccountProfile,
    AccountRole,
    AccountSyncAssessment,
    BotAssessment,
    DataOrigin,
    InteractionType,
    MediaAttachment,
    UnifiedSocialEvent,
)


def bot(score: float, coverage: float = 0.9) -> BotAssessment:
    return BotAssessment(
        computation_mode="HEURISTIC_INDICATOR",
        analysis_status="AVAILABLE",
        parameter_set_id=Parameters().parameter_set_id,
        coverage_ratio=coverage,
        evidence_reasons=["Boundary test input"],
        feature_contributions={"controlled_feature": score},
        bot_indicator_score=score,
        observed_posts=3,
        observation_seconds=360,
        available_feature_weights={"sync_tightness": coverage},
    )


def sync(score: float) -> AccountSyncAssessment:
    return AccountSyncAssessment(
        computation_mode="COMPUTED_PIPELINE",
        analysis_status="AVAILABLE",
        parameter_set_id=Parameters().parameter_set_id,
        coverage_ratio=1,
        evidence_reasons=["Boundary test input"],
        feature_contributions={"peer": score},
        sync_score=score,
        matched_peer_count=1,
        repeated_bucket_count=3,
    )


def test_parameter_weights_are_deeply_immutable_and_keys_are_complete() -> None:
    parameters = Parameters()
    with pytest.raises(TypeError):
        parameters.BOT_FEATURE_WEIGHTS["sync_tightness"] = 0
    with pytest.raises(TypeError):
        parameters.CTI_WEIGHTS.update({"sync": 0})
    with pytest.raises(ValueError):
        Parameters(BOT_FEATURE_WEIGHTS={"arbitrary": 1})


@pytest.mark.parametrize(
    "score,synchrony,coverage,expected",
    [
        (70, 0.65, 0.9, AccountRole.BOT_AMPLIFIER),
        (69.999, 0.65, 0.9, AccountRole.UNCLASSIFIED),
        (70, 0.64999, 0.9, AccountRole.UNCLASSIFIED),
        (49.999, 0.44999, 0.60, AccountRole.ORGANIC_USER),
        (50, 0.44999, 0.9, AccountRole.UNCLASSIFIED),
        (49, 0.45, 0.9, AccountRole.UNCLASSIFIED),
        (49, 0.44, 0.5999, AccountRole.UNCLASSIFIED),
    ],
)
def test_role_thresholds_and_seed_precedence(
    repository: EvidenceRepository,
    source: SourceEvent,
    score: float,
    synchrony: float,
    coverage: float,
    expected: AccountRole,
) -> None:
    service = IngestionService(repository)
    events = []
    for author in ("a", "b"):
        for index in range(3):
            events.append(
                service.ingest(
                    source.model_copy(
                        update={
                            "source_event_key": f"{author}-{index}",
                            "account": AccountProfile(
                                account_id=f"simulator:{author}", handle=f"@{author}"
                            ),
                            "timestamp_utc": source.timestamp_utc + timedelta(seconds=index * 180),
                        }
                    ),
                    scope="test",
                )
            )
    base = CoordinationEngine(Parameters()).analyze(events, similarity=lambda _a, _b: 0)
    reports = CoordinationResult(
        base.assessment,
        {author: sync(synchrony) for author in base.accounts},
        {author: bot(score, coverage) for author in base.bots},
        [],
        frozenset(),
    )
    nodes = GraphEngine(Parameters()).build(events, reports).nodes
    assert (
        next(node for node in nodes if node.id == "simulator:a").role
        == AccountRole.EARLIEST_OBSERVED_SEED
    )
    assert next(node for node in nodes if node.id == "simulator:b").role == expected


def test_observed_bridge_links_coordination_to_low_indicator_community(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    service = IngestionService(repository)
    events: list[UnifiedSocialEvent] = []
    ids: dict[tuple[str, int], str] = {}
    authors = ("a", "b", "c", "bridge", "low1", "low2")
    for wave in range(3):
        for index, author in enumerate(authors):
            parent_author = {"bridge": "a", "low1": "bridge", "low2": "low1"}.get(author)
            event = service.ingest(
                source.model_copy(
                    update={
                        "source_event_key": f"{author}-{wave}",
                        "account": AccountProfile(
                            account_id=f"simulator:{author}", handle=f"@{author}"
                        ),
                        "timestamp_utc": source.timestamp_utc
                        + timedelta(seconds=wave * 180 + index),
                        "interaction_type": InteractionType.REPOST
                        if parent_author
                        else InteractionType.ORIGINAL_POST,
                        "parent_event_id": ids.get((parent_author, wave))
                        if parent_author
                        else None,
                    }
                ),
                scope="test",
            )
            ids[(author, wave)] = event.event_id
            events.append(event)
    base = CoordinationEngine(Parameters()).analyze(events, similarity=lambda _a, _b: 0)
    group = {"simulator:a", "simulator:b", "simulator:c"}
    bots = {
        author: bot(90 if author in group else 60 if author == "simulator:bridge" else 10)
        for author in base.bots
    }
    scores = {author: sync(0.95 if author in group else 0.2) for author in base.accounts}
    edges = [
        SyncEdge(
            "simulator:a",
            f"simulator:{peer}",
            0.95,
            tuple(PairMatch(ids[("a", wave)], ids[(peer, wave)], 1, wave * 3) for wave in range(3)),
        )
        for peer in ("b", "c")
    ]
    result = CoordinationResult(base.assessment, scores, bots, edges, frozenset(group))
    graph = GraphEngine(Parameters()).build(events, result)
    assert (
        next(node for node in graph.nodes if node.id == "simulator:bridge").role
        == AccountRole.BRIDGE_INFLUENCER
    )
    assert all(
        node.role == AccountRole.ORGANIC_USER
        for node in graph.nodes
        if node.id.startswith("simulator:low")
    )
    assert any(edge.interaction_type == "BRIDGE_TRANSFER" for edge in graph.edges)


def test_recompressed_related_media_excludes_self(repository: EvidenceRepository) -> None:
    original = media_bytes("baseline")
    with Image.open(BytesIO(original)) as image:
        compressed = BytesIO()
        image.save(compressed, "JPEG", quality=91)
    with repository.transaction() as db:
        a, _ = repository.put_artifact(
            db, original, "MEDIA", "image/jpeg", DataOrigin.USER_INJECTED, "test"
        )
        b, _ = repository.put_artifact(
            db, compressed.getvalue(), "MEDIA", "image/jpeg", DataOrigin.USER_INJECTED, "test"
        )
    report = MediaEngine(repository, "test").verify(a, comparison_ids=(a, b, a))
    assert report.duplicate_matches_count == 1
    assert (
        MediaEngine(repository, "test").verify(a, comparison_ids=(a,)).duplicate_matches_count == 0
    )


def test_exact_observation_span_boundary(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    events = []
    for author in range(4):
        for index, seconds in enumerate((0, 90, 180)):
            events.append(
                IngestionService(repository).ingest(
                    source.model_copy(
                        update={
                            "source_event_key": f"{author}-{index}",
                            "account": AccountProfile(
                                account_id=f"simulator:{author}", handle=f"@p{author}"
                            ),
                            "timestamp_utc": source.timestamp_utc + timedelta(seconds=seconds),
                        }
                    ),
                    scope="test",
                )
            )
    result = CoordinationEngine(Parameters()).analyze(events, similarity=lambda _a, _b: 1)
    assert result.assessment.sync_score is not None
    assert all(report.sync_score is not None for report in result.accounts.values())


def test_pipeline_related_phash_links_text_dissimilar_coposts(
    repository: EvidenceRepository, source: SourceEvent, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.pipeline import Pipeline
    from app.repositories.state import StatePartition, StateRepository

    state = StateRepository(repository, "test")
    pipeline = Pipeline(state)
    vectors = {
        "anchor": [1, 0],
        "left": [(1 - 0.3**2) ** 0.5, 0.3],
        "right": [(1 - 0.3**2) ** 0.5, -0.3],
    }
    monkeypatch.setattr(
        pipeline.nlp,
        "embed",
        lambda texts: np.asarray([vectors.get(text, [0, 0]) for text in texts], dtype=np.float64),
    )
    with Image.open(BytesIO(media_bytes("baseline"))) as image:
        buffer = BytesIO()
        image.save(buffer, "JPEG", quality=91)
    attachments = []
    with repository.transaction() as db:
        for index, data in enumerate((media_bytes("baseline"), buffer.getvalue())):
            ref, digest = repository.put_artifact(
                db, data, "MEDIA", "image/jpeg", source.data_origin, "test"
            )
            attachments.append(
                MediaAttachment(
                    media_id=str(index),
                    media_type="image",
                    sha256_hash=digest,
                    evidence_ref=ref,
                    collection_status="COLLECTED",
                )
            )
    partition = StatePartition(
        data_origin=source.data_origin, collector_scope=source.collector_scope
    )
    for author, text, media in (
        ("anchor", "anchor", None),
        ("x", "left", attachments[0]),
        ("y", "right", attachments[1]),
        ("z", "left", attachments[0]),
    ):
        for wave in range(1 if media is None else 3):
            observed = source.model_copy(
                update={
                    "source_event_key": f"{author}-{wave}",
                    "text": text,
                    "account": AccountProfile(
                        account_id=f"simulator:{author}", handle=f"@{author}"
                    ),
                    "timestamp_utc": source.timestamp_utc
                    + timedelta(seconds=-10 if media is None else wave * 120 + ord(author) - 120),
                    "media_attachments": (media,) if media else (),
                }
            )
            pipeline.activate(observed, partition, 0)
    details, _ = pipeline.refresh(partition, 0)
    assert len(details) == 1
    assert details[0].coordination_assessment.sync_score is not None
    assert details[0].coordination_assessment.sync_score > 0.65
