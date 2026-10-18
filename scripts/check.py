"""Run the phase gate with fail-fast exit status on Windows or Linux."""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    python = sys.executable
    checks = [
        ([python, "-m", "pip", "check"], root),
        ([python, "-m", "pytest", "backend/tests", "-q"], root),
        ([python, "-m", "ruff", "check", "backend", "scripts"], root),
        ([python, "-m", "ruff", "format", "--check", "backend", "scripts"], root),
        ([python, "-m", "mypy", "backend/app", "--ignore-missing-imports"], root),
        ([python, "backend/scripts/generate_types.py", "--check"], root),
        (
            ["npm.cmd" if sys.platform == "win32" else "npm", "run", "typecheck"],
            root / "frontend",
        ),
        (
            ["npm.cmd" if sys.platform == "win32" else "npm", "run", "format:check"],
            root / "frontend",
        ),
        (
            ["npm.cmd" if sys.platform == "win32" else "npm", "run", "build"],
            root / "frontend",
        ),
        ([python, "scripts/smoke.py"], root),
    ]
    for command, directory in checks:
        subprocess.run(command, cwd=directory, check=True)


if __name__ == "__main__":
    main()
