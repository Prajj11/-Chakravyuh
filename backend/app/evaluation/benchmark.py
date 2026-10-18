"""Declared local timing samples; no thresholds or analytical outputs are changed."""

import json
import os
import platform
import statistics
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Parameters, Settings
from app.coordination.engine import CoordinationEngine
from app.graph_engine.engine import GraphEngine
from app.ingestion.contracts import SourceEvent
from app.ingestion.service import IngestionService
from app.ingestion.simulator import SCENARIO_IDS, fixture_root, ingest_scenario, replay_scope
from app.main import create_app
from app.pipeline import Pipeline
from app.reporting.exporter import Exporter
from app.repositories.evidence import EvidenceRepository
from app.repositories.state import StatePartition, StateRepository
from app.schemas.models import (
    AccountProfile,
    DataOrigin,
    ExportRequest,
    InteractionType,
    PlatformType,
)


def timed(function: Callable[[], object], samples: int) -> dict[str, object]:
    values = []
    for _ in range(samples):
        start = time.perf_counter()
        function()
        values.append((time.perf_counter() - start) * 1000)
    ordered = sorted(values)
    return {
        "samples_ms": values,
        "sample_count": samples,
        "median_ms": statistics.median(values),
        "p95_ms": ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))],
        "maximum_ms": max(values),
    }


def run(output: Path) -> None:
    if output.exists():
        raise FileExistsError("Benchmark outputs are never overwritten")
    output.parent.mkdir(parents=True, exist_ok=True)
    runtime = fixture_root().parent / ".runtime"
    runtime.mkdir(exist_ok=True)
    p = Parameters()
    with TemporaryDirectory(dir=runtime, prefix="benchmark-") as temporary:
        root = Path(temporary)
        repo = EvidenceRepository(root / "state", p)
        try:
            state = StateRepository(repo)
            init_start = time.perf_counter()
            pipeline = Pipeline(state)
            initialization_ms = (time.perf_counter() - init_start) * 1000
            events = list(ingest_scenario(SCENARIO_IDS[0], pipeline.ingestor, scope="local"))[:100]
            partition = StatePartition(
                data_origin=DataOrigin.SYNTHETIC_REPLAY,
                collector_scope=replay_scope(SCENARIO_IDS[0]),
            )
            for event in events:
                state.record_account(partition, 0, event.event_id)
            scoring_cold = timed(lambda: pipeline.refresh(partition, 0), 1)
            scoring_warm = timed(lambda: pipeline.refresh(partition, 0), 5)
            detail = state.list_campaigns()[0]
            export_cold = timed(
                lambda: Exporter(state).export(
                    detail.campaign_id, ExportRequest(), "local-analyst:benchmark"
                ),
                1,
            )
            export_warm = timed(
                lambda: Exporter(state).export(
                    detail.campaign_id, ExportRequest(), "local-analyst:benchmark"
                ),
                5,
            )
            token = "benchmark-local-session-token-" + "x" * 32
            with TestClient(
                create_app(Settings(data_dir=root / "state", session_token=SecretStr(token))),
                base_url="http://127.0.0.1",
            ) as client:
                path = f"/api/v1/campaigns/{detail.campaign_id}"
                headers = {"Authorization": "Bearer " + token}

                def read() -> None:
                    response = client.get(path, headers=headers)
                    if response.status_code != 200:
                        raise RuntimeError("Benchmark read failed")

                rest_cold = timed(read, 1)
                rest_warm = timed(read, 30)
            graph_repo = EvidenceRepository(root / "graph", p)
            try:
                graph_events = []
                parent = None
                for index in range(1000):
                    source = SourceEvent(
                        source_event_key=f"node-{index}",
                        platform=PlatformType.SIMULATOR,
                        data_origin=DataOrigin.SYNTHETIC_REPLAY,
                        collector_id="benchmark-v1",
                        collector_scope="graph-1000",
                        timestamp_utc=datetime(2026, 10, 1, tzinfo=UTC) + timedelta(seconds=index),
                        account=AccountProfile(
                            account_id=f"simulator:benchmark-{index:06d}",
                            handle=f"@observer_{index:06d}",
                        ),
                        text=f"Observed reply {index}",
                        interaction_type=InteractionType.REPLY
                        if parent
                        else InteractionType.ORIGINAL_POST,
                        parent_event_id=parent,
                    )
                    event = IngestionService(graph_repo).ingest(source, scope="local")
                    graph_events.append(event)
                    parent = event.event_id
                coordination = CoordinationEngine(p).analyze(
                    graph_events, similarity=lambda _a, _b: 0
                )
                graph = GraphEngine(p)
                graph_cold = timed(lambda: graph.build(graph_events, coordination), 1)
                graph_warm = timed(lambda: graph.build(graph_events, coordination), 3)
                graph_repo.verify("local")
            finally:
                graph_repo.close()
            result = {
                "graph_backend": "rustworkx 0.17.1 exact sequential Brandes; NetworkX 3.5 Louvain",
                "version": "local-benchmark-v1",
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "hardware": {
                    "platform": platform.platform(),
                    "processor": platform.processor(),
                    "logical_cpus": os.cpu_count(),
                },
                "python": platform.python_version(),
                "parameter_set_id": p.parameter_set_id,
                "embedding_mode": pipeline.nlp.mode.value,
                "pipeline_initialization_ms": initialization_ms,
                "batch": {"events": 100, "media": "one retained JPEG", "history": "none"},
                "scoring": {"cold": scoring_cold, "warm": scoring_warm},
                "export": {"cold": export_cold, "warm": export_warm},
                "rest_detail": {
                    "transport": "in-process ASGI TestClient; excludes TCP/browser overhead",
                    "cold": rest_cold,
                    "warm": rest_warm,
                },
                "graph_1000": {
                    "topology": "1000 nodes / 999 directed reply edges; "
                    "exact normalized betweenness + Louvain",
                    "cold": graph_cold,
                    "warm": graph_warm,
                },
                "targets_ms": {
                    "rest_p95": 200,
                    "scoring_100": 2000,
                    "graph_1000": 800,
                    "export_100": 2000,
                },
                "limitations": [
                    "Local synthetic workloads only; "
                    "no throughput, GPU or 5000-node browser claim.",
                    "Cold means first operation in this process; "
                    "warm reuses loaded models/fonts and OS caches.",
                    "Fixture capture and model initialization are "
                    "reported/excluded from operation timing.",
                ],
            }
            output.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(
                json.dumps(
                    {
                        "scoring_warm_median_ms": scoring_warm["median_ms"],
                        "export_warm_median_ms": export_warm["median_ms"],
                        "rest_warm_p95_ms": rest_warm["p95_ms"],
                        "graph_warm_median_ms": graph_warm["median_ms"],
                    },
                    indent=2,
                )
            )
        finally:
            repo.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("evaluation/results/performance-v1.json")
    )
    run(parser.parse_args().output)
