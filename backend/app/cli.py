"""Local evidence foundation commands; no analytical outputs are fabricated."""

import argparse
import sys
from io import TextIOWrapper
from pathlib import Path

from app.config import Parameters, Settings
from app.ingestion.contracts import SourceEvent
from app.ingestion.service import IngestionService
from app.repositories.evidence import EvidenceRepository


def main() -> None:
    if isinstance(sys.stdout, TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["ingest", "verify"])
    parser.add_argument("source", type=Path, nargs="?")
    parser.add_argument("--scope", default="local")
    args = parser.parse_args()
    repository = EvidenceRepository(Settings().data_dir, Parameters())
    try:
        if args.command == "verify":
            print(repository.verify(args.scope))
        else:
            if args.source is None:
                parser.error("ingest requires a source JSON file")
            source = SourceEvent.model_validate_json(args.source.read_bytes())
            result = IngestionService(repository).ingest(source, scope=args.scope)
            print(result.model_dump_json(indent=2))
    finally:
        repository.close()


if __name__ == "__main__":
    main()
