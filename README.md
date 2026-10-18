# Chakravyuh

Local-first investigation of public social content, coordinated amplification indicators,
media anomalies and geographic context. The ten files in [`docs v2`](docs%20v2/) are the
active v2.1.0 specification.

## Implemented foundation

- FastAPI, Pydantic v2 wire models, central analytical defaults and parameter-set hashing.
- Canonical JSON with golden-vector tests, exact raw captures/manifests, separate raw/event/media
  hashes, SQLite metadata and content-addressed bytes.
- Idempotent ingestion, deeply immutable events, append-only audit chain, late media records,
  analytical-run lineage and integrity verification.
- Local session authorization, exact loopback CORS, validated image upload and protected downloads.
- Next.js/React/strict TypeScript/Tailwind shell with live backend telemetry, keyboard-accessible
  preview tabs and session connection. Shared TypeScript models are generated from Python.

This is an implementation starting point, not the complete MVP. Replay scenarios, analytical
engines, campaign snapshots, queued injection, WebSockets, claim review and dossier exports are
pending. Campaign listing is currently empty. The UI labels these states and shows no fabricated
findings. Only JPEG, PNG and WebP uploads are supported in this slice; other media returns 415.

## Windows startup

Double-click `start.bat` to install missing dependencies and launch the backend and
frontend in separate terminals. Open http://127.0.0.1:3000 when they are ready. Stop each service
with Ctrl+C. `start.bat --check` checks prerequisites without starting services. Close any
previous instances before launching again.

Verified with Windows, Python 3.12.10 and Node.js 24.18.0. Python 3.11+ and Node.js 20.9+ are the
declared minimums; other runtime combinations have not yet been tested. Native asyncio is used.
No Docker, GPU, model downloads, credentials or cloud services are required.

Run from the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c backend/requirements.lock -e './backend[dev]'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --loop asyncio
```

In a second terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open [the workbench](http://127.0.0.1:3000) and [API documentation](http://127.0.0.1:8001/docs).
The backend uses port 8001 to avoid an existing local service on 8000. Both services bind to
loopback. Stop each with Ctrl+C. Production preview: `npm run build`, then `npm run start`.

The backend writes a fresh per-launch token to `.runtime/local-session-token`. Read it locally
and paste it into the workbench session field. It is not printed by the server or served through
HTTP. Mutation, campaign and artifact routes require `Authorization: Bearer <token>`. The token
field is cleared after authorization and is not stored in browser storage. The UI session is
currently a connection check; later mutation controls are still disabled.

Optional configuration: copy `backend/.env.example` to `.env` in the repository root, and
`frontend/.env.example` to `frontend/.env.local`. If changing ports, set the frontend API URL and
the exact `CHAKRAVYUH_FRONTEND_ORIGIN` consistently. Browser API URLs are compiled into production
builds. Use `127.0.0.1` consistently; `localhost` is a different CORS origin.

## Exercise ingestion and integrity

On Linux, run `./scripts/dev.sh` from a clean clone (Python 3.12 and Node.js 24 recommended).
It creates the virtual environment, installs locked dependencies and starts both services;
Ctrl+C stops them. Initial dependency installation needs network access; the installed
runtime and offline smoke test need none. `make setup`, `make check`, `make test` and
`make demo` provide matching shortcuts. Windows `start.bat --setup` refreshes dependencies.
CI is configured for Linux and Windows; remote CI results have not yet been observed.

With the Python environment installed, run from the root:

```powershell
.\.venv\Scripts\python.exe -m app.cli ingest sample_data/raw/local-example.json
.\.venv\Scripts\python.exe -m app.cli verify
```

The example is visibly `USER_INJECTED`, uses a simulator-qualified account, and contains no
analysis labels. Repeating it is idempotent. HTTP connector adapters must pass the original
entity bytes explicitly; injection/replay source objects use canonical JSON. `--scope` selects
an independent repository access partition; the application uses `local`.

`.runtime/metadata.sqlite3` contains metadata and chained audit records; `.runtime/evidence/`
contains content-addressed raw, canonical and media bytes. These paths are gitignored. Evidence
is retained across restarts; do not edit it. The verifier fails on changed/missing registered
bytes, canonical divergence and broken audit links. Local hashes provide tamper evidence relative
to retained metadata, not external attestation or legal admissibility.

## Checks and contract generation

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\ruff.exe check backend
.\.venv\Scripts\ruff.exe format --check backend
.\.venv\Scripts\python.exe backend/scripts/generate_types.py --check
Set-Location frontend
npm run typecheck
npm run format:check
npm run build
```

After intentional Python schema changes, regenerate with
`.\.venv\Scripts\python.exe backend/scripts/generate_types.py` from the repository root.
Tests place isolated temporary data under `.runtime/test-tmp/`, avoiding shared Windows temp
permissions. `backend/requirements.lock` pins the resolved Windows Python dependencies;
`frontend/package-lock.json` locks the frontend tree. The backend constraints include platform
markers for Windows dependencies. The test client uses httpx2. Python source is checked with
`python -m mypy backend/app --ignore-missing-imports`; `python scripts/smoke.py` verifies offline
CLI ingestion, idempotency and evidence integrity.

See [`tasks-v2.md`](docs%20v2/tasks-v2.md) and [`memory-v2.md`](docs%20v2/memory-v2.md) for actual
completion status and remaining acceptance work. Accuracy and performance targets remain
unmeasured.
