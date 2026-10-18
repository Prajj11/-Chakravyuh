#!/usr/bin/env bash
# Bash job control gives each service its own process group for complete cleanup.
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

case "${1:-}" in
  --check) exec bash "$ROOT_DIR/scripts/setup.sh" --check ;;
  --help|-h)
    printf 'Usage: ./scripts/dev.sh [--check]\nInstall missing dependencies and start the local workbench.\nOptional environment: API_PORT=8001 FRONTEND_PORT=3000 PYTHON=python3\n'
    exit 0
    ;;
  '') ;;
  *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
esac

if (( BASH_VERSINFO[0] < 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] < 3) )); then
  printf 'scripts/dev.sh requires Bash 4.3 or newer.\n' >&2
  exit 1
fi
bash "$ROOT_DIR/scripts/setup.sh"

API_PORT="${API_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
export CHAKRAVYUH_FRONTEND_ORIGIN="http://127.0.0.1:$FRONTEND_PORT"
export NEXT_PUBLIC_API_URL="http://127.0.0.1:$API_PORT"
export NEXT_TELEMETRY_DISABLED=1
"$ROOT_DIR/.venv/bin/python" - "$API_PORT" "$FRONTEND_PORT" <<'PY'
import socket
import sys

try:
    ports = [int(value) for value in sys.argv[1:]]
    if len(set(ports)) != 2 or any(not 1 <= port <= 65535 for port in ports):
        raise ValueError("API_PORT and FRONTEND_PORT must be distinct ports from 1 to 65535")
    for port in ports:
        with socket.socket() as server:
            server.bind(("127.0.0.1", port))
except (OSError, ValueError) as error:
    sys.exit(f"Cannot start local services: {error}")
PY

BACKEND_PID=''
FRONTEND_PID=''
cleanup() {
  trap - EXIT INT TERM
  for service_pid in "$BACKEND_PID" "$FRONTEND_PID"; do
    if [[ -n "$service_pid" ]]; then
      # A service may already have exited; terminate its remaining descendants too.
      kill -TERM -- "-$service_pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
set -m

"$ROOT_DIR/.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" --loop asyncio &
BACKEND_PID=$!
(
  cd "$ROOT_DIR/frontend"
  exec node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

printf '\nWorkbench: http://127.0.0.1:%s\nAPI docs:  http://127.0.0.1:%s/docs\nPress Ctrl+C to stop both services.\n\n' "$FRONTEND_PORT" "$API_PORT"
set +e
wait -n "$BACKEND_PID" "$FRONTEND_PID"
SERVICE_STATUS=$?
set -e
printf '\nA service exited (status %s); stopping the workbench.\n' "$SERVICE_STATUS" >&2
exit "$SERVICE_STATUS"
