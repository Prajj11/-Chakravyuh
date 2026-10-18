"""Detect dependency input changes before reusing a Windows development environment."""

import argparse
import hashlib
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for filename in (
        "backend/pyproject.toml",
        "backend/requirements.lock",
        "frontend/package.json",
        "frontend/package-lock.json",
    ):
        digest.update(filename.encode())
        digest.update(b"\0")
        digest.update((root / filename).read_bytes())
    expected = digest.hexdigest() + "\n"
    stamp = root / ".venv" / ".chakravyuh-windows-dependencies.sha256"
    if args.write:
        stamp.write_text(expected, encoding="utf-8")
    elif not stamp.is_file() or stamp.read_text(encoding="utf-8") != expected:
        raise SystemExit(
            "Dependencies changed or setup is unrecorded. Run start.bat --setup."
        )


if __name__ == "__main__":
    main()
