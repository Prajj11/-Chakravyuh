"""Exercise installed CLI ingestion, idempotency and evidence verification offline."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from app.config import Parameters
from app.ingestion.service import IngestionService
from app.ingestion.simulator import SCENARIO_IDS, ingest_scenario, replay_scope
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
        "Offline smoke passed: idempotent CLI, three replay scenarios, isolated reset and verified hashes."
    )


if __name__ == "__main__":
    main()
