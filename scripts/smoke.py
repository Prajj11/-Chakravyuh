"""Exercise installed CLI ingestion, idempotency and evidence verification offline."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from app.config import Parameters
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import UnifiedSocialEvent


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
        finally:
            repository.close()
    print(
        "Offline CLI smoke passed: one immutable event, one audit entry, verified hashes."
    )


if __name__ == "__main__":
    main()
