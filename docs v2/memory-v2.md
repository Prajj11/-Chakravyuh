# Project Memory and Decision Log: Chakravyuh

**Contract version:** 2.1.0  
**Updated:** October 18, 2026  
**Current state:** Evidence foundation and frontend preview implemented; analytical pipeline and complete MVP remain pending.
**Next task:** T-1.3 / T-1.4 raw replay fixtures, followed by narrative analytics; finish context-dependent T-0.3 validators as services arrive.

## 1. Active specification

The ten Markdown files in docs v2 are the complete active contract. They supersede historical docs v1; filenames retain -v2 for continuity. Do not read a shorter v2 document as an implicit supplement to v1.

| Owner | Contract |
|---|---|
| Product scope and acceptance | PRD-v2.md |
| Algorithms, units, thresholds and runtime constraints | trd-v2.md |
| Enums, typed payloads, endpoints and persistence | backendschema-v2.md |
| Architecture and boundaries | architecture-v2.md |
| Engineering, privacy, public-only collection and review rules | rules-v2.md |
| UI behavior and investigation flows | design-v2.md, appflow-v2.md |
| Execution and actual progress | implementationplan-v2.md, tasks-v2.md, this file |

On disagreement, resolve the owning specification and update dependent documents. No software has been built or evaluated by this documentation revision.

## 2. Core interpretation

Chakravyuh is a local-first evidence-based investigation workbench for coordination, media indicators and geographic trends. Claim verification is a separate context-reviewed assessment. High synchrony does not itself prove orchestration, automation, malicious intent or falsity.

EARLIEST_OBSERVED_SEED is the earliest author in the observed dataset, with deterministic tie-breaking and collection limits. It does not mean globally original or suspicious. ORGANIC_USER means low observed indicators under sufficiency gates; UNCLASSIFIED covers uncertain/intermediate cases.

All outputs are computed from observed inputs. Input origin is independently PUBLIC_OSINT, USER_INJECTED or SYNTHETIC_REPLAY. Canonical computation modes:
- COMPUTED_PIPELINE
- COMPUTED_ELA_PHASH
- HEURISTIC_INDICATOR
- MODEL_INFERENCE
- SIMULATED_FIXTURE_METADATA (test annotations only; excluded from scoring)

Claim statuses are UNVERIFIED, CONTRADICTED_BY_SOURCE, CORROBORATED and CONTEXT_MISSING. Retrieval similarity alone is not verification. No synthetic advisory verifies public/injected claims.

## 3. Accepted decisions

### ADR-001: Local-first and reproducible

Use SQLite, content-addressed local evidence, NumPy and NetworkX with CPU image processing. Models may use cached weights; frozen TF-IDF is explicitly limited fallback. Public connectors are optional best-effort features. Cloud/GPU/map tokens are not prerequisites for offline acceptance.

### ADR-002: Immutable evidence and separate hash domains

Retain and separately hash raw capture bytes, canonical normalized event serialization and exact media bytes. Canonical events exclude their own hash and never include mutable campaign memberships. Preserve capture manifest, source key/URL and wall-clock collection time. Later media/enrichment is appended. Verify artifacts and chained audit records before export; integrity mismatch fails export.

### ADR-003: Explicit uncertain outputs

Every analytical report includes method/status, input coverage, missing signals, evidence reasons, contributions, pipeline version and parameter-set ID. Missing scores are null, distinct from measured zero. Bot/ELA numbers are indicators, not calibrated probabilities.

### ADR-004: Repeated coordination and explicit scaling

Pair matching requires content linkage, disjoint selected pairs across >=2 minute buckets and inclusive 0-60s deltas. Normalize q_uv=1-exp(-sum(exp(-delta/20))). Account/campaign aggregation, feature scaling and sufficiency are fully specified in the TRD. Single-burst synchrony alone is insufficient. MVP burst dispersion is not a fitted Hawkes model.

### ADR-005: Role precedence

Temporal seed first, then qualifying bot amplifier, bridge influencer, sufficiently observed low-indicator user, otherwise UNCLASSIFIED. No high-degree cutoff replaces the earliest observed account. Unknown identities across platforms remain separate.

### ADR-006: Geographic coverage and historical scope

Author GPS/resolved declared profile differs from mentioned subject. Mismatch requires GMR>=0.60, source coverage>=0.30, >=10 known-source posts, >=5 known-source authors and campaign sync>=0.65. Regional Z requires >=168 valid same-scope hourly buckets from the preceding 30 days. No history yields null Z. Raw replay history produces labelled synthetic baselines.

### ADR-007: CTI score versus alert eligibility

Base weights remain .30 sync, .25 bot density, .20 media, .15 geo and .10 harm; renormalize available components and expose coverage. Unavailable sync means unavailable CTI. Tiers on unrounded scores: LOW [0,40), MEDIUM [40,60), HIGH [60,75), CRITICAL [75,100].

Critical-tier CTI does not alone dispatch an alert. Require CTI>=75, component coverage>=0.60, campaign sync>=0.65, scored-post coverage>=0.30, >=10 campaign posts and >=5 authors. TRD owns cooldown/rearm and all numerical defaults. A provisional score may have a numeric tier while its alert is suppressed.

### ADR-008: Human review, privacy and truthful forensics

Claim status requires a contextual reference and authenticated reviewer/time. ELA/pHash and metadata are indicators; C2PA reports real adapter state. Video/audio without evaluated adapters is unsupported. Default redaction includes low-indicator and unclassified participants and omits restricted originals from redacted bundles. A local dossier is investigative material, not guaranteed legal admissibility or statutory compliance.

### ADR-009: Async work and complete frontend delivery

Heavy mutation endpoints return 202 jobs, including export; reads/polling and typed WebSocket events expose completion. Scenario resets are generation-safe and panels use coherent snapshot revisions. Frontend and release verification are mandatory backlog phases, not implicit follow-up work.

## 4. Threshold maintenance

trd-v2.md Section 2 is the authoritative constants table; implement it centrally in backend/app/config.py. Important retained boundaries are semantic cosine 0.85, temporal window 60s, bot indicator 70, synchronization 0.65, geographic spike Z=3 and critical CTI=75.

The new evidence/sample gates are chosen MVP defaults to validate on calibration data, not established scientific guarantees. Any change requires parameter-set versioning, dependent documentation updates and relevant tests. Never tune held-out tests or fake outputs to obtain a target demo badge.

## 5. Changelog and current verification

### October 18, 2026 — Phase 0 hardening

- Added Linux setup/dev scripts, Makefile, Windows auto-setup launcher, portable dependency constraints and Linux/Windows CI. Initial installation needs network; installed runtime is offline. CI configuration is present; remote Linux/Windows CI execution is not claimed.
- Switched the Starlette test client to httpx2, added mypy, MIME-derived download names, and tested upload authorization before multipart parsing. Health reads the actual registered layer states; pending engines remain degraded.
- The supplied master prompts disagree on pairing buckets; the owning TRD and second prompt specify one-minute buckets, which remain authoritative. The documented three scenario IDs are retained; additional benign controls belong in evaluation. The requested frontend-design skill is unavailable, so the supplied design contract guides implementation.
- Windows phase gate: 39 backend tests, Ruff lint/format, mypy, generated contracts, frontend typecheck/format/build and offline CLI smoke pass. Linux execution remains unverified locally.

- **October 18, 2026 — v1:** Initial ten architecture/product documents created.
- **October 18, 2026 — v2.0:** Threshold and schema reconciliation introduced separate claim context, missing metadata and runtime-computed outputs.
- **October 18, 2026 — v2.1.0:** Corrected remaining enum inconsistencies, organic fallback, raw/canonical/media hashes, source capture lineage, report metadata and endpoint/job contracts. Specified synchronization normalization, bot scaling, geographic history/sample gates, CTI missing-component behavior and alert eligibility. Restored complete engineering/privacy rules, UI interactions, frontend backlog and release checks. Removed guaranteed scenario outputs and unsupported deepfake/Hawkes claims.

The documentation revision checked all ten file versions, 18 relative links, Python syntax for 53 documented classes and Pydantic v2 JSON-schema generation. Those checks did not constitute software implementation.

### October 18, 2026 — Initial implementation slice

- Completed T-0.2, T-0.4, T-1.1 and T-1.2. All documented Python wire models now exist; generated strict TypeScript mirrors include discriminated job/WebSocket unions. Structural validation covers finite scores, unavailable primary scores, additive contributions, job/payload pairings, UTC timestamps, media retention, geography and review prerequisites. Service-context checks (claim audit/context, engine sufficiency, crypto adapter verification, sequence state) remain pending under T-0.3.
- Implemented canonical-json-v1, exact source captures/manifests, immutable nested event fields, SQLite content-addressed evidence metadata, chained audit, concurrent idempotent ingestion, late media collection and analytical-run lineage. Evidence verification detects raw/canonical/media/analysis/manifest corruption, event divergence and audit chain changes. No export service exists yet.
- Added local bearer session, loopback/CORS defaults, APIError envelope, safe JPEG/PNG/WebP decoding/limits and scoped artifact downloads. API currently exposes health, empty campaigns, image upload and artifact download only. Other required endpoints are pending; no successful analytical responses are fabricated.
- Added Next.js/Tailwind preview with real health/event telemetry, pending analytical views, session authorization and responsive layout. Scenario/injection/export controls are disabled and visibly planned. This does not complete Phase 5.
- ADR-010: Backend default development port is 8001 because another service already occupied 8000. Frontend defaults to 127.0.0.1:3000; both bind to loopback. README includes environment overrides and Windows startup without activation/uvloop.
- Verified Windows / Python 3.12.10 / Node.js 24.18.0 with pinned dependency trees. Initial tests: 36 passed; Ruff lint/format, generated-contract check, frontend strict typecheck and production build passed. Follow-up checks recorded below. Starlette currently emits a dev-only httpx deprecation warning. Other OS/Python minimum combinations are untested.
- Smoke-tested CLI ingestion twice (one retained event/audit entry), integrity verification, live API telemetry and narrow in-app browser layout. Fixed Windows cp1252 console output by emitting UTF-8 in the CLI. Default shared pytest temp directory was inaccessible; tests now use isolated workspace-local temporary directories.
- No accuracy, latency, full replay journey, graph/map/forensics visual QA, multilingual PDF or redaction-export acceptance is claimed. Retained one clearly USER_INJECTED local example in gitignored runtime storage for the preview.
- Final foundation verification: 38 backend tests passed (one upstream Starlette/httpx deprecation warning); Ruff lint and format checks passed; TypeScript mirror regeneration check passed; frontend typecheck, Prettier check and production build passed; tracked diff whitespace check passed. Live browser confirmed API connection, one retained event, local-session authorization and arrow-key view-tab navigation. Persisted complete parameter-set JSON alongside its hash; parameter metadata is append-only and included in integrity verification. Preview services run locally on ports 3000 and 8001.

### October 18, 2026 — Phase 1 replay and durable state

- Completed T-1.3, T-1.4 and T-1.5: deterministic raw scenarios, actual baseline/spliced JPEGs, separate evaluation mask, local synthetic claim snapshots, multilingual harm registry, gazetteer and frozen training corpus. The three scenarios contain 108, 45 and 75 current events. Historical replay includes 240 covered hourly windows and raw observations; baseline counts are derived from observations, not target Z scores.
- Added durable partitioned active events, memberships, campaign snapshots, typed jobs, references/reviews and topic-specific baseline buckets. Reset creates a new replay generation and retains immutable evidence and other origins/scopes. Interrupted queued/running jobs fail explicitly on process restart. Replay clock supports speed changes, pause/resume and stale-generation rejection.
- 57 backend tests pass on Windows, including determinism, raw-label exclusion, media bytes, parent resolution, ingestion idempotency, partition isolation and serialized reset. No analytical scenario scores or accuracy claims exist yet. Public live connectors remain optional and unimplemented.
