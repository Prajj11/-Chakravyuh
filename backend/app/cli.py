"""Local evidence foundation commands; no analytical outputs are fabricated."""

import argparse
import json
import sys
from io import TextIOWrapper
from pathlib import Path

from app.config import Parameters, Settings
from app.ingestion.contracts import SourceEvent
from app.ingestion.service import IngestionService
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import DataOrigin


def main() -> None:
    if isinstance(sys.stdout, TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["ingest", "verify", "search"])
    parser.add_argument("source", type=Path, nargs="?")
    parser.add_argument("--scope", default="local")
    parser.add_argument("--query", default="", help="Literal case-sensitive text/event/account ID")
    parser.add_argument("--origin", choices=[origin.value for origin in DataOrigin])
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()
    repository = EvidenceRepository(Settings().data_dir, Parameters())
    try:
        if args.command == "verify":
            print(repository.verify(args.scope))
        elif args.command == "search":
            if not 1 <= args.limit <= 1000 or args.offset < 0:
                parser.error("Search limit must be 1–1000 and offset nonnegative")
            print(
                json.dumps(
                    [
                        event.model_dump(mode="json")
                        for event in repository.search_events(
                            args.query,
                            args.scope,
                            origin=DataOrigin(args.origin) if args.origin else None,
                            limit=args.limit,
                            offset=args.offset,
                        )
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
            )
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
