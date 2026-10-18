#!/usr/bin/env bash
# Install only when the locked dependency inputs change or an environment is missing.
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODE="${1:-install}"
case "$MODE" in
  install|--force|--check) ;;
  *) printf 'Usage: %s [--force|--check]\n' "$0" >&2; exit 2 ;;
esac

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  printf 'Install Node.js 24 (with npm), then run this command again.\n' >&2
  exit 1
fi
node -e 'const [major, minor] = process.versions.node.split(".").map(Number); if (major < 20 || (major === 20 && minor < 9)) { console.error("Node.js 20.9+ is required; Node.js 24 is recommended."); process.exit(1); }'

if [[ ! -x .venv/bin/python ]]; then
  if [[ "$MODE" == --check ]]; then
    printf 'Python environment missing; run ./scripts/setup.sh.\n' >&2
    exit 1
  fi
  if [[ -d .venv/Scripts ]]; then
    printf 'This checkout has a Windows virtual environment. Use start.bat on Windows or a separate checkout on Linux.\n' >&2
    exit 1
  fi
  PYTHON_BOOTSTRAP="${PYTHON:-python3}"
  if ! command -v "$PYTHON_BOOTSTRAP" >/dev/null 2>&1; then
    printf 'Install Python 3.12 (including its venv module), then run this command again.\n' >&2
    exit 1
  fi
  "$PYTHON_BOOTSTRAP" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ is required; Python 3.12 is recommended.")'
  "$PYTHON_BOOTSTRAP" -m venv .venv
fi
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
"$PYTHON_BIN" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "Recreate .venv with Python 3.11+.")'

dependency_hash() {
  "$PYTHON_BIN" - "$@" <<'PY'
import hashlib
import sys
from pathlib import Path

digest = hashlib.sha256()
for filename in sys.argv[1:]:
    digest.update(Path(filename).read_bytes())
print(digest.hexdigest())
PY
}

BACKEND_HASH="$(dependency_hash backend/pyproject.toml backend/requirements.lock)"
FRONTEND_HASH="$(dependency_hash frontend/package.json frontend/package-lock.json)"
BACKEND_STAMP=.venv/.chakravyuh-dependencies.sha256
FRONTEND_STAMP=frontend/node_modules/.chakravyuh-dependencies.sha256

if [[ "$MODE" != --check ]]; then
  if [[ "$MODE" == --force || ! -f "$BACKEND_STAMP" || "$(cat "$BACKEND_STAMP")" != "$BACKEND_HASH" ]]; then
    "$PYTHON_BIN" -m pip install -c backend/requirements.lock -e './backend[dev]'
    printf '%s\n' "$BACKEND_HASH" > "$BACKEND_STAMP"
  fi
  if [[ "$MODE" == --force || ! -f frontend/node_modules/next/dist/bin/next || ! -f "$FRONTEND_STAMP" || "$(cat "$FRONTEND_STAMP")" != "$FRONTEND_HASH" ]]; then
    (cd frontend && npm ci --no-audit --no-fund)
    printf '%s\n' "$FRONTEND_HASH" > "$FRONTEND_STAMP"
  fi
fi

"$PYTHON_BIN" -m pip check
"$PYTHON_BIN" -c 'import app.config, fastapi, uvicorn; from importlib.metadata import version; print("Backend ready: " + version("chakravyuh-backend"))'
if [[ ! -f frontend/node_modules/next/dist/bin/next ]]; then
  printf 'Frontend dependencies missing; run ./scripts/setup.sh.\n' >&2
  exit 1
fi
printf 'Startup prerequisites are available.\n'
