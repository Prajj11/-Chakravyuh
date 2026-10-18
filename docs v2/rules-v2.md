# Engineering, AI Assistant & OSINT Rules: Chakravyuh

**Contract version:** 2.1.0  
**Updated:** October 18, 2026  
**Scope:** Mandatory for implementation and maintenance.

## 1. Document authority and workflow

The ten files in docs v2 are the complete active specification and supersede docs v1. Filenames retain -v2. No v1 rule must be silently inherited. If a useful requirement is found in v1, reconcile and explicitly add it here before treating it as part of the active contract.

Read [memory-v2.md](memory-v2.md) and [tasks-v2.md](tasks-v2.md) before coding. PRD owns scope, TRD owns constants/algorithms, backend schema owns wire names and persistence, design/appflow own UI behavior. On disagreement, resolve the owning contract and update all affected references in the same change; do not silently choose an implementation.

After completing a feature, check only its actual completed task, record the decision/result in memory, and run the relevant checks. Documentation completion does not imply scaffolding or software completion.

## 2. Architecture and execution

Keep ingestion, nlp_engine, media_forensics, coordination, graph_engine, geo_engine, and reporting modular behind typed Pydantic contracts. API routes orchestrate services; core engines never import route/frontend code. Platform-specific parsing ends at ingestion; retained raw evidence remains accessible only through the evidence repository.

Use an async queue for orchestration and workers/executors for CPU-heavy inference, graph recalculation and rendering. Declaring a CPU function async does not make it nonblocking. Queued jobs and polling follow backendschema-v2.md; WebSocket broadcasts typed results. Failed workers return explicit status/reasons rather than fabricated successful scores.

Replay and live/injected data run through the same analytics. Isolate state by data_origin and collection scope; event-time controls analytics, wall-clock UTC records collection. Use platform-qualified identities. Simulators emit source objects, historical replay events and media bytes, not enriched events, labels-as-features or output scores.

## 3. Evidence, uncertainty and terminology

- Every score is calculated from observed inputs and includes computation_mode, analysis_status, parameter_set_id, pipeline_version, coverage_ratio, missing_signals, evidence_reasons and feature_contributions through the shared report model.
- Null denotes unavailable analysis; measured zero denotes an available negative/low indicator. Do not conceal missing features by substituting zeros. Handle all-missing and zero-denominator cases explicitly.
- Bot outputs are bot_indicator_score; retain the older BOT_PROBABILITY_HIGH_CUTOFF config key only as documented. No heuristic score is displayed as a calibrated probability or SHAP attribution.
- Use only the five ComputationMode enum values in backendschema-v2.md. SIMULATED_FIXTURE_METADATA is annotation-only and cannot feed scores, CTI, alerts or real claim findings.
- Record input data_origin independently of computation mode. Display SYNTHETIC_REPLAY throughout demo views and exports; computed results on synthetic data remain computed.
- Synchrony supports investigation of coordination; it does not prove orchestration, automation, malicious intent or falsity. Display claim verification separately.
- EARLIEST_OBSERVED_SEED is dataset-bounded and need not be malicious. Unknown/intermediate accounts are UNCLASSIFIED, never implicitly organic.
- Preserve exact raw and media bytes, canonical events and append-only audit records as the TRD specifies. Never mutate evidence or overwrite a hash-addressed artifact.
- ELA, perceptual similarity and missing metadata are indicators, not verified deepfakes. C2PA status reports actual adapter verification, not inferred camera origin.
- Packages are "Tamper-Evident Investigative Dossiers." Do not promise court admissibility, statutory compliance, or validated accuracy without supporting work.

## 4. Development conventions

Backend: Python 3.11+, complete function annotations, Pydantic v2 contracts with extra fields forbidden, Ruff lint/format with 100-character line length. Catch specific exceptions and log structured context without raw sensitive payloads. Reject NaN/infinite scores. Pin dependency versions after compatibility checks, including Windows; native asyncio is the default.

Frontend: Next.js App Router, React, TypeScript strict=true. No any or implicit any; use unknown at external boundaries and validate it. Keep generated/mirrored domain types in src/types/chakravyuh.ts. Use semantic Tailwind tokens and escaped content. Canvas/WebGL is required above 200 graph nodes; cap/debounce expensive recomputations and clean up simulations/WebSockets on unmount.

Set random seeds explicitly (42 default) for replay, ML sampling and Louvain. Freeze fitted vocabularies and model revisions per run. Stable tie-breaking uses IDs. Preserve reproducible event-time results while recording actual collection times.

## 5. Public-data access, privacy and security

Collect only publicly accessible content through permitted endpoints. Never bypass authentication, access controls, platform limits, private groups or direct messages. Connectors use allowlisted sources, timeouts/backoff, declared collection scope and resumable cursors; 403/429 pauses collection rather than switching to evasive scraping. Live connectivity is optional for MVP acceptance.

Bind local services to loopback by default. Protect mutation, claim-review, export, upload and artifact routes with a per-launch local session; derive reviewer identity server-side. A remote deployment requires configured authentication, authorization and HTTPS and is outside local MVP acceptance. Configure CORS for the actual frontend origin, not wildcard credentialed access. Downloads and evidence refs enforce the same session scope.

Limit uploads to 25 MiB; verify decoded content and MIME, not just extensions. MVP supported images: JPEG, PNG, WebP. Video MP4 and audio WAV/MP3 can be retained but return UNSUPPORTED when adapters are absent. Reject decompression bombs/oversized dimensions, malformed files and unsafe paths. Never execute uploaded content. Uploaded URLs are not arbitrary fetch instructions; connector downloads follow source allowlists and exclude local/private network targets.

Release adapter coverage: the HTTP upload accepts JPEG/PNG/WebP and structurally validated WAV. MP4/MP3 upload decoders remain unimplemented; retained video/audio fixtures may report UNSUPPORTED. Do not imply all listed containers can currently be uploaded. Audio/video inference and C2PA verification are unavailable.

Default UI anonymization and exported redaction cover ORGANIC_USER and UNCLASSIFIED accounts. Apply masking consistently to post text mentions, labels, account metadata, STIX and all reports. Raw evidence is restricted; sanitized copies are separately hashed derivatives. Display privacy controls before download. Do not export originals inside a purportedly redacted package.

Local UI/WebSocket warnings are automatic. No automatic takedowns, external incident dispatch or official submission. Those integrations are deferred; if added, require a concrete review/confirmation step before sending outside the workbench. Creating a local downloadable dossier does not send it to another organization.

## 6. Verification requirements

Each analytical engine needs meaningful tests for output contracts, empty/insufficient data and its distinctive behavior. Cover simultaneous timestamps, repeated evidence, denominator failures, missing/unsupported geography/media, score boundaries, benign coordination and false positives.

Before marking a feature complete: run its focused unit/integration tests and contract validation. Before release: run backend pytest/Ruff, frontend typecheck/build, end-to-end scenario/injection/export checks and visual QA of graph/map/timeline/forensics states. PDF export must be visually inspected, including multilingual text and redaction.

Performance and accuracy numbers remain targets until measured on declared hardware and held-out datasets. Record actual results and limitations in memory-v2.md; never alter fixtures or tests merely to force a desired CTI badge.
