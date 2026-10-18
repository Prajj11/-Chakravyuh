"""Exercise installed CLI ingestion, idempotency and evidence verification offline."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from app.config import Parameters
from app.coordination.engine import CoordinationEngine
from app.geo_engine.engine import GeoEngine
from app.graph_engine.engine import GraphEngine
from app.ingestion.service import IngestionService
from app.ingestion.simulator import SCENARIO_IDS, ingest_scenario, replay_scope
from app.media_forensics.engine import MediaEngine
from app.nlp_engine.engine import NarrativeEngine
from app.repositories.evidence import EvidenceRepository
from app.repositories.state import StatePartition, StateRepository
from app.schemas.models import DataOrigin, UnifiedSocialEvent


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    runtime = root / ".runtime"
    runtime.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="cli-smoke-", dir=runtime) as temporary:
        environment = dict(os.environ, CHAKRAVYUH_DATA_DIR=temporary, PYTHONUTF8="1")
        events: list[UnifiedSocialEvent] = []
        for _ in range(2):
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "app.cli",
                    "ingest",
                    "sample_data/raw/local-example.json",
                ],
                cwd=root,
                env=environment,
                check=True,
                capture_output=True,
            )
            events.append(UnifiedSocialEvent.model_validate_json(result.stdout))
        if events[0] != events[1]:
            raise RuntimeError(
                "Repeated CLI ingestion must return the retained immutable event"
            )
        subprocess.run(
            [sys.executable, "-m", "app.cli", "verify"],
            cwd=root,
            env=environment,
            check=True,
        )
        repository = EvidenceRepository(Path(temporary), Parameters())
        try:
            counts = repository.verify("local")
            if counts["events"] != 1 or counts["audit_entries"] != 1:
                raise RuntimeError(f"CLI ingestion was not idempotent: {counts}")
            state = StateRepository(repository)
            nlp = NarrativeEngine(repository.parameters)
            for scenario in SCENARIO_IDS:
                events = ingest_scenario(
                    scenario, IngestionService(repository), scope="local"
                )
                partition = StatePartition(
                    data_origin=DataOrigin.SYNTHETIC_REPLAY,
                    collector_scope=replay_scope(scenario),
                )
                generation = state.generation(partition)
                for event in events:
                    state.record_account(partition, generation, event.event_id)
                for cluster in nlp.cluster(events, partition_id=partition.key):
                    members = [
                        event for event in events if event.event_id in cluster.event_ids
                    ]
                    vectors = nlp.embed([event.text for event in members])
                    indices = {
                        event.event_id: index for index, event in enumerate(members)
                    }
                    result = CoordinationEngine(repository.parameters).analyze(
                        members,
                        similarity=lambda a, b, vectors=vectors, indices=indices: float(
                            np.clip(
                                np.dot(
                                    vectors[indices[a.event_id]],
                                    vectors[indices[b.event_id]],
                                ),
                                0,
                                1,
                            )
                        ),
                    )
                    repository.record_analysis(
                        result.assessment,
                        [event.canonical_event_sha256 for event in members],
                        {nlp.model_id: nlp.revision},
                        partition.data_origin,
                        "local",
                    )
                    graph = GraphEngine(repository.parameters).build(members, result)
                    if sum(
                        bucket.coordinated_volume
                        + bucket.low_indicator_volume
                        + bucket.unclassified_volume
                        for bucket in graph.timeline
                    ) != len(members):
                        raise RuntimeError(
                            "Timeline does not partition the observed events"
                        )
                    GeoEngine(repository.parameters).analyze(
                        members,
                        all_events=events,
                        partition=partition,
                        sync_score=result.assessment.sync_score,
                        baselines=[],
                    )
                media_ids = {
                    attachment.evidence_ref
                    for event in events
                    for attachment in event.media_attachments
                    if attachment.evidence_ref
                }
                for media_id in media_ids:
                    MediaEngine(repository).verify(
                        media_id, comparison_ids=tuple(media_ids)
                    )
                if state.list_events(partition) != sorted(
                    events, key=lambda event: (event.timestamp_utc, event.event_id)
                ):
                    raise RuntimeError(
                        "Replay events differ from retained active state"
                    )
                state.reset_replay(partition.collector_scope)
                if state.list_events(partition):
                    raise RuntimeError("Reset left active replay events")
            repository.verify("local")
        finally:
            repository.close()
    print(
        "Offline smoke passed: CLI, three replay scenarios, frozen NLP, coordination, reset and integrity."
    )


if __name__ == "__main__":
    main()
