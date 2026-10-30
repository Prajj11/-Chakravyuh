# Project Memory and Decision Log: Chakravyuh

**Contract version:** 2.1.0  
**Updated:** October 19, 2026

**October 23 YouTube validation:** Configured the user-supplied YouTube credential only in
git-ignored local connector settings. Official API discovery using the supplied Bihar
cybercrime topic selected public video `ItsVeXu01nQ`; local feed polls every 300 seconds.
One real comment response normalized and ingested 34 public comments, repeat ingestion
added zero events, evidence verification passed, and the dashboard campaigns API returned
HTTP 200 with one public campaign in an isolated test store. See
`evaluation/results/youtube-api-smoke-2026-10-23.json`. Restart is required for an existing
backend to load the new local feed. This validates the top-level-comment adapter for one
video, not video deepfake inference or disinformation accuracy.

**October 23 audit:** Compared `Cluade.docx` with current source. Live public adapters,
webhook delivery, media diagnostics and supervised evaluation were added since that older
assessment. Fixed HN fuzzy-result pollution, lost titles, malformed-row handling, repeated
cursors, ingestion recovery after refresh failure, and blank queries; restored the documented
live launcher entry point. Real HN check: 100/100 Bihar matches after the fix versus 0/100
before, 100 ingested, zero duplicate re-ingestions, evidence verified. Validation: 25 focused
tests passed in 9.52 seconds, Ruff passed on changed Python files, and the repository's
mypy command passed across 53 source files. Historical corpus
verification passed for 10,084 records / 617 responses. See the
[full feature/crawler audit](feature-crawler-audit-2026-10-23.md) for current capabilities
and limitations; earlier release-gap entries below are chronological.

**Current state:** Offline investigation workbench implemented through Phase 6, with recorded synthetic evaluation and explicit release gaps. Windows local verification is complete; this is a demonstration release, not a production accuracy claim.
**Next work:** Prioritize the organizer-only dataset migration requested October 19. The user confirmed the two TXT files are the complete supplied input and public collection using their keywords is allowed. A standalone Hacker News collector produced 10,084 verified public records from 5,821 authors, including 187 explicit Bihar mentions; see [collection report](../datasets/public-corpus-report.md). This predominantly cybersecurity corpus is unlabelled and not yet imported into the dashboard. Bihar-focused source coverage, competition workflow isolation, actual-data model evaluation, graph latency and archive browsing remain open.

**Dataset extension:** 25 additional fictional source cases / 7,500 posts / 1,500 accounts are available through Scenario studio. See `sample_data/case_pack/README.md`; source cases can split into multiple detected narratives.

## 1. Active specification

The October 19 [hackathon roadmap](hackathon-roadmap.md) is a separate prioritized proposal. It does not add implemented capabilities or override the ten versioned contracts below.

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

On disagreement, resolve the owning specification and update dependent documents. The chronological entries below distinguish earlier foundation checkpoints from the current implemented and evaluated release.

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

### October 18, 2026 — Phase 2 analytical engines

- Implemented frozen word/character TF-IDF, recorded corpus/alias revision, optional explicit local 384-dimensional multilingual model, event-time clustering, null zero-vector assignment semantics, candidate retrieval and multilingual exact-phrase harm indicators. Optional model weights are not installed or evaluated. Raw evidence text is unchanged.
- Implemented inclusive 0–60s content-linked matching, deterministic disjoint pairing, minute-bucket repetition, exponential normalized edges, account/campaign aggregation, descriptive completed-minute burst dispersion, and five availability-weighted bot features. No model probability or Hawkes result is fabricated.
- Added contextual review service with retained snapshot hash, authenticated reviewer, origin/date/region checks and audit. T-2.2 remains in progress until endpoint integration and journey tests in Phase 4. All other Phase 2 engine tasks pass their focused checks.
- Parameter revision 2.1.0.1 centralizes previously specified algorithm constants without changing defaults. 69 Windows backend tests pass. Offline smoke exercises all scenarios through frozen NLP/coordination and retains verifiable analytical lineage. Accuracy remains unmeasured; synthetic repeated text is not general multilingual validation.

### October 18, 2026 — Phase 3 graph, media and geography

- Added directed parent-to-amplifier/reply edges, separate q-weighted sync edges, deterministic Louvain communities and directed-interaction normalized betweenness. Role precedence, low-indicator gates and timeline partitioning are computed from observations; unresolved parents are omitted. Bridge eligibility uses observed group/low-community links, with no inferred identities.
- Added exact-media DCT64 pHash, RGB Q90 ELA, unamplified percentile scores, 8-connected regions with overlap merging, retained PNG heatmaps and real EXIF presence. C2PA is NOT_CHECKED. Unsupported video/audio scores remain null; malformed images fail explicitly. No fixture mask enters scoring.
- Added resolved declared-profile/GPS sources separately from mentioned targets, H3 resolution-5 mismatch, sample/coverage/sync gates, topic-v1 scope hashes and 30-day covered-hour mean/sample-deviation baselines. Fewer than 168 valid matching hours yields null Z; zero known sources yields null mismatch.
- Windows full phase gate passes: 74 tests, Ruff/format, mypy, generated contracts, frontend typecheck/format/build and expanded offline smoke through graph/geo/media. Evaluation F1 and ELA localization IoU are still unmeasured; the synthetic mask is reserved for evaluation.

### October 18, 2026 — Phase 4 integrated backend

- All eleven REST endpoints and authenticated WebSocket transport are implemented. CPU pipeline work uses one executor behind a typed queue, durable terminal jobs and generation checks. Tests cover reset during replay, typed sequence recovery, injection and contextual review. WebSocket authentication uses the chakravyuh.v1 subprotocol plus the session token, keeping credentials out of URLs. T-4.3 awaits the Phase 5 browser polling/reconnect implementation.
- Added available-component CTI, unrounded tiers, suppression gates, event-time cooldown and continuous rearm. Replay pacing honors speed_multiplier; current snapshots are rebuilt atomically and reports retain source hashes and model/parameter lineage. No scenario score is forced.
- Added integrity-gated ZIP exports containing dossier, observations, HTML/PDF, STIX 2.1, hash manifest and disclaimer. Default organic/unclassified redaction applies uniformly, including decoded STIX payloads; restricted originals are omitted. Export corruption tests fail with EVIDENCE_INTEGRITY_MISMATCH. Audit manifests represent the prefix before their own export to avoid self-referential hashes; the export action remains in the local ledger.
- Fixed upload-body limits during receipt without Content-Length and retained valid WAV containers with UNSUPPORTED analysis. MP4/MP3 upload decoders remain unimplemented; image and WAV upload are the supported API types. Video inference, C2PA verification and audio inference remain explicitly unavailable.
- PDF QA caught mixed-font Hindi spacing. Bundled Noto Latin/Devanagari tables were combined with fonttools 4.60.1; uharfbuzz shapes both in one embedded font. Rendered multilingual PDF inspected successfully using bundled PDFium. Font sources and SIL license are retained.
- Full Windows gate: 87 tests, Ruff/format, mypy (38 sources), contract generation, frontend checks/build and offline smoke pass. Full frontend and held-out evaluation remain pending; no release-complete claim is made.

### October 18, 2026 — Phase 5 investigation workbench

- Replaced the preview with live campaign feeds, one-revision detail panels, CTI/suppression breakdown, Canvas d3-force graph, role/sync/cascade filters, convex community hulls, searchable keyboard node list and account/edge inspector. Timeline, geography and selected-account observations share visual filters while retaining the original analytical scores.
- Added H3 source/target arcs, scope/coverage/sample explanations, local Natural Earth/MapLibre/Deck.gl rendering and an always-available SVG coordinate fallback. This machine exercised the fallback when WebGL was unavailable. No external tiles, font services or tokens are required.
- Added authenticated original/ELA slider, anomaly boxes, full hashes/pHash/EXIF/C2PA/unsupported states; synthetic-reference warnings and contextual review; queued injection with optional actor/time/GPS/declared location/media; and redacted format-selectable export with verified download.
- Added generated runtime JSON schemas and Zod boundary validation, strict shared TypeScript types, in-memory session authorization, sequence-aware WebSocket reconnect/backoff and three-second REST polling. Default participant masking is used in labels/mentions. Queued scenarios automatically select their computed result on completion.
- Windows gates pass: 87 backend tests; Ruff/format/mypy/contracts; frontend strict typecheck, formatting, production build and npm audit (zero findings); offline smoke; two Playwright journeys (44.1s on the final run). Browser journeys cover graph/map/media/review/export manifest checks, injection surviving reset, new-session resync and 390px layout. Screenshots inspected for graph, map, geographic mismatch, media, timeline and narrow layout. E2E CI is configured for Linux Chromium and Windows Edge; remote CI is not claimed.
- Measured demo outputs at seed 42 during browser QA: electoral CTI approximately 87.5, sync 0.680; geo CTI approximately 95.4, sync 0.896, GMR 0.818, Z 38.83 with 240 covered hours. These are computed observations, not acceptance constants. Natural-discussion and held-out control evaluation remain for Phase 6.

### October 18, 2026 — Phase 6 verification and demonstration release

- Closed engine/API boundary coverage: inclusive timing and sufficiency thresholds, role priority, exact centrality, recompressed pHash content linkage, late media enrichment, zero/missing geography, unavailable CTI inputs, corruption/export blocking, chunked body limits and early authorization. Review publication re-reads the latest locked snapshot and preserves a review arriving during computation. Parameter weight dictionaries reject mutation.
- Added audit-anchored immutable analytical run manifests binding origin/access scope, input hashes, parameters, implementation revisions and report hash. Method reference artifacts retain frozen corpus, aliases, harm phrases, gazetteer, topic dictionary and library versions. Existing runs are disclosed as legacy rather than backfilled with invented historical anchors. Verification rehashes all files; a bounded cache lasts for only one verification call.
- Cached MiniLM wiring now selects compatible local CPU weights when available and records file-derived revision; invalid/unavailable caches fall back explicitly. Weights are not installed here, so MODEL_INFERENCE accuracy/execution remains unverified. Late collected media feeds reports and coordination without changing original events. NEW_EVENT/CTI_ALERT use observation/watermark event time; job/control notices use wall-clock time. Alert markers are actual stream notifications rather than inferred from CTI tier.
- Default feed summaries mask restricted identity text at the server, selected views also mask display-name mentions, and dossier derivatives additionally remove restricted source GPS/H3/region. Explicit authorized unredacted summaries remain available with redact_pii=false. Default UI privacy does not remove retained evidence.
- Replaced NetworkX exact betweenness execution with mathematically equivalent sequential Rustworkx 0.17.1 Brandes, deterministic node/edge ordering and 15 random-graph parity cases against NetworkX (absolute 1e-12). NetworkX 3.5 Louvain seed/resolution and analytical thresholds remain unchanged. Bounded verification reads and compiled privacy matching reduce export overhead.
- Frozen calibration before one held-out fallback test; no threshold changes or test rescoring. Train/calibration/test use disjoint topic families, account IDs, templates and seeds, 45 cases each. Test F1/precision/recall 1.00 on 36 labelled cases (18 TP, 0 FP, 0 FN); 27/45 primary results are insufficient. Benign mobilisation is coordination-positive and alert-negative, with 0/9 gated alerts. Each language has 12 labelled cases, F1 1.00, 9/15 insufficient results and 0/3 benign alerts. Calibration F1 0.8571 (6 FP) is retained. These bilingual synthetic templates do not validate broad multilingual accuracy or intent inference.
- ELA mask IoU 1.00 on one reserved synthetic mask, one region. This is exploratory localization, not a representative forgery benchmark. Reports preserve source/mask hashes and explicitly show unsupported model-mode evaluation. Evaluation integrity verified 1,260 events, 3,784 artifacts and 1,261 audit entries.
- Performance v2 on Windows 11 / AMD64 Family 25 Model 116 Stepping 1 / 16 logical CPUs / Python 3.12.10: 100-event/one-JPEG scoring cold 491 ms, warm median 425 ms (5 runs); verified export cold 877 ms, warm median 719 ms (5); in-process ASGI detail cold 102 ms, warm P95 26 ms (30). No TCP/browser overhead is included. Initialization 37 ms is separate; fixture capture is excluded. Graph chain 1,000 nodes/999 edges cold 884 ms, warm median 834 ms, maximum 895 ms (3): **800 ms target unmet**. Unmodified performance-v1/v2 reports retain before/after samples. No 5,000-node/500-event-per-second claim.
- Local checks: 124 pytest cases; Ruff lint/format, mypy (44 app sources), generated TypeScript/runtime schemas, frontend strict TypeScript/format/production build, dependency consistency and offline smoke. Three Edge journeys passed (1.8 minutes): all scenarios; graph/map/media; claim review and ZIP manifest validation; injected origin surviving reset/reload; forced socket interruption and reconnect; natural-discussion alert suppression; 390px layout and no external requests in the main journey. start.bat --setup reinstalled locked dependencies and --check passed; changed dependency inputs invalidate its setup stamp. npm audit reported zero vulnerabilities. All seven pages of the actual multilingual PDF were rendered and visually inspected; font layout and margins are correct. CI remains configured, not remotely observed.
- Remaining explicit gaps: graph target, deferred archive search UI/API for older evidence, Linux/remote CI confirmation, optional model validation and real-world evaluation. Older injections are retained with EVENT_RETAINED_OUTSIDE_ACTIVE_WINDOW and remain searchable through the CLI across retained generations. CLI search is literal/case-sensitive with origin/access-scope filters and bounded pagination; tests cover reset, older observations and scope isolation. Optional public connectors, MP4/MP3 upload decoders, audio/video inference, C2PA and fitted Hawkes remain unavailable. Local session is not multi-user production authentication.

| Frozen identity | SHA-256 / revision |
|---|---|
| Parameter set (2.1.0.1) | `475d31789d485a11d2128556a8bfbf16122e3d730a95f707091be36078747d8a` |
| Training dataset | `46ece118e1e716ed7d5bca8eeaceb0d9ae104c6981e227eecd5c9ab7a24fa020` |
| Calibration dataset | `8f42d839fad617662e70bbaedeb535f90988823fd97bc30620b85cc4702fd24d` |
| Test dataset | `ed4ffbe90b8977a6eb69c4bc409e183114ec5018ece2f4c4e3fd6c448903375d` |
| Frozen training corpus | `c97b681643532b135cffeff439d118092293265bc7dab58e5e71d4858ec43568` |
| TF-IDF revision | `tfidf-v1:1b285a21a7b4db67a6f94ed0c1828992acb792c86a0eb9b7c29d4c65ef54ac4b` |
| ELA evaluation mask | `fdc53f916bebeb2d57f32b030ac6329c334ed170f78e67500cf3a2b1b0f7072d` |

Full evaluation protocol, raw metrics, limitations and reproduction commands are in [evaluation/README.md](../evaluation/README.md). README now describes the implemented workbench, Windows/Linux entry points, optional weights, a five-minute demonstration and actual release gaps.

- Live launch verification: backend healthy and frontend HTTP 200 through the Windows launcher subcommands. Followed bundled Next.js 16.4 guidance: keep next-env.d.ts generated/gitignored, run next typegen before typechecking a fresh checkout, and retain the framework-generated AGENTS.md. Development startup no longer changes tracked framework type declarations.

### October 18, 2026 — Windows launch and API entry-page fix

- Added setup/check and separate backend/frontend BAT entry points. The main launcher checks port availability before starting services, waits for API health and frontend HTTP readiness, then opens the workbench at port 3000. Individual service starts also check their own port; occupied ports produce clear instructions before another backend can overwrite the session token file.
- GET / on the backend now serves an API landing page linking the configured frontend origin, API docs and health. It exposes no session token and does not change protected API authorization. Service terminal messages distinguish the workbench address from API documentation.
- Verified 125 backend tests, Ruff lint/format, mypy and generated-contract consistency; exercised readiness against both running services and confirmed duplicate-start guards for both ports. The landing page test covers a custom frontend port and continued authorization enforcement. Frontend runtime code is unchanged; the existing three browser journeys remain the UI verification record. Existing running services require a restart to load the new backend root route.


### October 19, 2026 — Investigation UI redesign and hackathon roadmap

- Reworked the local session entry and investigation workspace with a Chakra SVG mark, local typography, teal/charcoal surfaces, clearer case hierarchy, four compact signal cards, collapsible assessment details, and responsive graph/map/media layouts. Scenario studio is explicitly opened from the header; default privacy masking remains visible through a persistent toggle.
- Added campaign search over displayed titles/languages/origin and All cases / Warnings / Unverified filters. Warnings means current backend alert eligibility; queue filters do not recompute scores or change the selected case.
- Added a deterministic Investigation brief, derived only from the selected snapshot, linking to the strongest measured co-post edge, earliest observed seed, media reports and independent claim review. Brief-to-tab navigation moves keyboard focus to the destination tab. This is presentation logic, not new ML inference or claim attribution.
- Updated design/appflow and completed T-5.10/T-5.11. Added hackathon-roadmap.md as a proposal outside the ten versioned contracts, ranking narrative evolution, historical as-of analysis and benign-coordination challenges first. None of those proposed analytical features is implied to be implemented.
- Verification: frontend typecheck, Prettier checks and optimized production build pass. All three Edge browser journeys pass (2.2 minutes), covering search/filter behavior, brief links, score explanations, graph/map/media, claim review, integrity-verified ZIP/PDF download, injection/reset, origin preservation, reconnection and suppressed natural discussion. The affected full investigation/export journey passed again (37.9 seconds) after the keyboard-focus follow-up. The main journey confirms no page errors, no external requests and no horizontal overflow at 390 px.
- Visual QA: inspected actual production graph, geographic context, image comparison, natural-discussion and narrow layouts, plus the session entry and refreshed desktop preview. Captures live under .runtime/ui-redesign-*.png; test artifacts remain local and ignored. Checks used a separate .runtime/ui-preview backend store, leaving the normal local data store unchanged. Backend analytical code, schema and dependencies did not change; existing graph-latency and model/connector/evaluation limitations still apply.


### October 19, 2026 — Diverse case pack and batch replay

- Added 25 reproducible synthetic source cases with 7,500 posts, 1,500 distinct accounts and 25 cities. Each case has 60 accounts and five waves; the pack has 2,500 posts each in English, Hindi and Hinglish. Twenty percent of accounts lack location observations. Repost/reply references, profile/GPS distinctions and outside-city declarations are raw input fields.
- Six cases use synchronized generation, four staggered, six mixed, four benign mobilisation and five ordinary discussion. These names are generator intentions and never become detector labels or target scores. Each post visibly identifies itself as a synthetic exercise. Seven cases reuse the generic baseline/spliced JPEG fixtures; voice/video references are text-only. No new historical baseline or fact-check verdict is fabricated.
- Exported 25 JSONL files (10,171,124 bytes total) with SHA-256 manifest and a generated frontend menu. `python -m app.ingestion.case_pack --check` verifies the generator, seed-42 exports and menu remain identical. Runtime replay regenerates the same source records for the selected seed.
- Added backend-allowlisted demo IDs and `expanded` group; `all` retains its original three-scenario meaning. TIMED is still the API default. The UI defaults expanded selections to BATCH, disables the ineffective speed setting and explains that intermediate warning times are not replayed. Batch loading computes complete cases with the existing engines and emits one representative event notification per case; final job completion triggers the normal snapshot refresh.
- Added an evidence-artifact lookup index on hash/kind/origin/scope to avoid repeated table scans during larger imports. No evidence bytes, audit immutability or analytical thresholds were changed.
- Verification: all 128 backend tests passed in 322.11 seconds. The full-pack test authenticated the API, rejected unknown scenarios, ran the queued BATCH job and verified all 7,500 posts and 1,500 accounts in dashboard snapshots. The actual local run took 261.4 seconds and yielded 98 detected narratives at seed 42 with the lexical fallback. This is one Windows validation measurement, not a sustained-throughput or real-world accuracy claim.
- Ruff lint/format, mypy (46 source files), generated contract checks, dataset regeneration check, frontend typecheck/format and optimized production build passed. The new production Edge journey passed in 11.2 seconds (14.5 seconds including runner setup), verifying all 25 choices, batch/timed controls, a real 300-post case, privacy-aware search and no page errors/horizontal overflow at 390 px. Desktop/mobile images were visually inspected.
- Browser verification used the production UI with browser-only API/WebSocket redirection to a separate loopback test backend and `.runtime/case-pack-ui` store. The full-pack backend test used a separate test database. Normal user data was not reset by these checks. Local verification artifacts are `.runtime/case-pack-pytest.log`, `.runtime/case-pack-browser.log` and `.runtime/case-pack-browser-results/`.
