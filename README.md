# Chakravyuh

A local investigation workbench for observed coordination, image anomalies and geographic
context. Raw observations become immutable evidence, explainable campaign snapshots and
integrity-checked investigative dossiers. The active specification is in [`docs v2`](docs%20v2/).

## Start on Windows

1. Install Python 3.12 and Node.js 24, then double-click **`start.bat`**.
2. Wait for the backend and frontend terminals to become ready. Open
   [the workbench](http://127.0.0.1:3000).
3. Read `.runtime/local-session-token` locally and paste it into **Local session token**.
   Click **Connect session**. The field clears; the token stays in memory for this page session.
4. Select a replay scenario and click **Load raw scenario**. Default 100× replay completes
   the longest scenario in about a minute, plus calculation time.

The launcher creates `.venv`, installs missing or changed locked dependencies and starts both loopback services
in separate terminals. Initial installation requires internet access; the installed application,
fixtures, fonts and default map work offline. Stop both terminals with Ctrl+C before relaunching.
`start.bat --setup` refreshes locked dependencies; `start.bat --check` checks prerequisites.
The default ports are **8001** for the API and **3000** for the UI.

Tested locally on Windows 11, Python 3.12.10, Node.js 24.18.0 and Microsoft Edge. The declared
minimums are Python 3.11 and Node.js 20.9; other combinations have not been verified.
Linux entry point: `./scripts/dev.sh`. Linux/Windows CI is configured; remote CI and Linux
runtime results have not been observed here.

## What is implemented

- Three deterministic raw replay scenarios, event-time pacing, durable jobs and generation-safe
  replay reset; injected observations survive replay reset. Public, injected and synthetic
  origins and collector scopes have separate analytical state.
- Frozen multilingual word/character TF-IDF clustering, candidate claim retrieval, authenticated
  contextual review and English/Hindi/Hinglish phrase-based harm indicators. A compatible
  cached multilingual MiniLM model can be selected; it is never downloaded automatically.
- Content-linked, disjoint repeated co-post matching; availability-weighted bot indicators;
  directed observed interactions, separate sync edges, Louvain communities and exact directed
  betweenness. Every score records coverage, missing signals, reasons and parameter identity.
- Actual JPEG ELA and 64-bit pHash, retained heatmaps and anomaly boxes; H3 source/subject
  separation, geographic mismatch gates and topic/scope-specific historical baselines.
- Coverage-weighted CTI, separate alert eligibility, cooldown/rearm, sequenced WebSockets,
  reconnect and REST polling. Numeric tiers can be high while evidence gates suppress alerts.
- Responsive graph, geographic view, propagation timeline, account/edge inspection, image
  comparison, claim review, event/media injection and verified ZIP downloads.
- Append-only audit chain, separate raw/canonical/media SHA-256 domains, hash-bound analytical
  run manifests and integrity-gated PDF/HTML/JSON/STIX 2.1 packages. Default dossier redaction
  masks organic/unclassified participants and omits their original attachments.

These are investigative indicators. Coordination does not establish automation, intent or
falsity; earliest observed seed is bounded by collection. Claim similarity remains UNVERIFIED
until contextual human review. Synthetic advisories are visibly labelled and cannot verify
public or user-injected observations. Missing values stay null rather than becoming zero.

## Five-minute demonstration

1. Load **Electoral amplification**. Inspect CTI contributions and suppression gates, then
   select an account or sync edge to inspect observations, matched IDs and time deltas.
2. Use the role/sync/cascade controls and timeline cursor. These filter the view; they do not
   recalculate analytical scores. Open **Media**, compare original/ELA and inspect hash/status.
3. Open **Claims**, read the synthetic advisory warning and record a contextual review note.
   Export the default redacted dossier, wait for verification and download the completed ZIP.
4. Inject a separate observation. Load **Geographic mismatch**, confirm the replay reset,
   and open **Geography** to inspect source coverage, H3 mismatch and matching baseline hours.
   The injected campaign remains in the feed.
5. Load **Natural discussion**. Inspect its suppressed warning and low/unknown observations.
   Refresh the page, authorize again and confirm persisted snapshots return.

The map uses a bundled coordinate/SVG fallback and an optional local WebGL outline view.
Browsers without WebGL keep the fallback. No external map tiles, hosted fonts or map tokens
are required. Evidence retained through earlier runs remains on disk; reset changes active
replay generations rather than deleting the ledger.

## Configuration and manual startup

Optional: copy `backend/.env.example` to `.env` in the repository root. Use
`frontend/.env.example` as the frontend configuration reference. If changing ports, set
`NEXT_PUBLIC_API_URL` and the exact `CHAKRAVYUH_FRONTEND_ORIGIN` consistently; production UI
API URLs are compiled at build time. Use `127.0.0.1` consistently because `localhost` is a
different browser origin. API documentation is at [port 8001/docs](http://127.0.0.1:8001/docs).

From the root in PowerShell:

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

For a production preview, run `npm run build` and `npm run start` in `frontend`.
The per-launch token is never served over HTTP or put in a WebSocket URL. Protected routes
require `Authorization: Bearer <token>`; the browser sends WebSocket credentials as subprotocols.
The UI does not persist the token in browser storage. This is a single local analyst session,
not a hosted multi-user authentication system.

Optional model inference requires installing `./backend[nlp]` and retaining compatible weights
in `models/paraphrase-multilingual-MiniLM-L12-v2`, or setting `CHAKRAVYUH_CACHED_MODEL_DIR`.
Local CPU loading uses `local_files_only=True` and disables remote code. Missing/unusable
weights select the explicit frozen fallback. Optional inference is not covered by the reported
accuracy results and is outside the mandatory dependency lock.

## Verification and reproducibility

Run the complete local phase gate, then the browser journeys:

```powershell
.\.venv\Scripts\python.exe scripts/check.py
Set-Location frontend
npm run test:e2e
```

Browser tests start the backend and production frontend if their ports are free. Their default
data directory is `.runtime/e2e`. If reusing a manually running backend, set `PW_TOKEN_FILE` to
its token file before the browser command. Windows uses installed Edge; on Linux first run
`npx playwright install --with-deps chromium`. `make check`, `make smoke` and `make demo`
are also available. `scripts/check.py` includes pytest, Ruff lint/format, mypy, generated
contract consistency, frontend strict TypeScript/format/build and offline smoke.

Python wire models generate both TypeScript and runtime JSON schemas. After intentional schema
changes, run `.\.venv\Scripts\python.exe backend/scripts/generate_types.py`, then review both
generated files. Engine outputs pass typed validators; HTTP and WebSocket responses are checked
again at the frontend boundary.

Local release verification: **124 backend tests and three Edge browser journeys pass**,
along with the complete phase gate, a locked reinstall, startup prerequisite check and npm
audit (zero reported vulnerabilities). The actual seven-page English/Hindi dossier and desktop/
narrow layouts were rendered and visually inspected. Remote CI results remain unobserved.

The recorded frozen-fallback test F1 is **1.00 on 36 labelled synthetic cases**, with **0/9**
gated alerts on benign mobilisation controls. **27/45** test cases have insufficient primary
campaign evidence. Hindi/Hinglish cases are bilingual templates; these numbers do not establish
general multilingual or production accuracy. ELA localization IoU is **1.00 on one reserved
synthetic mask**. No pretrained-model accuracy is claimed. Full split hashes, calibration,
per-language results and limitations are in [`evaluation/README.md`](evaluation/README.md).

Windows measurements after optimization (100-event batch with one retained JPEG):

| Operation | Cold | Warm | Target |
|---|---:|---:|---:|
| Scoring | 491 ms | 425 ms median | <2,000 ms |
| Verified export | 877 ms | 719 ms median | <2,000 ms |
| Detail read, in-process ASGI | 102 ms | 26 ms P95 | <200 ms |
| 1,000-node graph, exact centrality + Louvain | 884 ms | 834 ms median | <800 ms **unmet** |

These are local synthetic workloads, not network latency or sustained throughput claims.
The unmodified before/after measurements are retained under `evaluation/results`.

## Evidence and current limits

The CLI supports `python -m app.cli ingest sample_data/raw/local-example.json` and
`python -m app.cli verify` after installing the environment. Retained text/event/account IDs
can be searched with `python -m app.cli search --query "observation" --origin USER_INJECTED`
(case-sensitive; `--limit`/`--offset` paginate; `--scope` selects the access partition). Identical ingestion is idempotent.
`.runtime/metadata.sqlite3` retains metadata/audit; `.runtime/evidence/` retains addressed bytes.
Runtime data and tokens are gitignored. Integrity verification rehashes every registered file
and checks canonical linkage, analytical manifests and audit anchors before export. Older
pre-upgrade analytical runs are explicitly reported as lacking anchored lineage manifests.
Local hashes provide tamper evidence relative to retained metadata, not external attestation.

- Public Reddit/Telegram connectors remain optional and unimplemented.
- Upload accepts JPEG, PNG, WebP and structurally valid WAV, bounded to 25 MiB and 24 MP for
  images. WAV analysis is UNSUPPORTED; MP4/MP3 upload decoders, audio/video inference, C2PA
  verification and fitted Hawkes estimation are unavailable, with no fabricated scores.
- Observations older than the active 24-hour window are retained. Injection returns
  `EVENT_RETAINED_OUTSIDE_ACTIVE_WINDOW`; retained-evidence CLI search includes them and prior
  replay generations. An archive search UI/API is deferred.
- Pretrained-model evaluation, representative real-world validation, Linux execution and remote
  CI confirmation remain unverified. The graph latency target is unmet on this machine.
- 5,000-node browser rendering, 500 events/second, external incident dispatch and production
  infrastructure are outside this local demonstration release.

See [`tasks-v2.md`](docs%20v2/tasks-v2.md), [`memory-v2.md`](docs%20v2/memory-v2.md) and
[`architecture-v2.md`](docs%20v2/architecture-v2.md) for implementation history and release gaps.
