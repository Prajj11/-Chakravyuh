# Engineering Backlog and Release Checks: Chakravyuh

**Contract version:** 2.1.0  
**Updated:** October 18, 2026  
**Tracking:** [x] completed, [/] in progress, [ ] pending. Documentation completion does not imply working software.

## Phase 0: Contracts and scaffolding

- [x] **T-0.1:** Reconcile all ten v2 docs to 2.1.0: enums, unknown roles, provenance, algorithms, coverage/gates, endpoints, UI, governance and full backlog.
- [x] **T-0.2:** Initialize backend/, frontend/, sample_data/ and development configuration; retain docs v2 as active documentation.
- [/] **T-0.3:** Implement typed schemas and central config including validators, parameter-set hashing and TypeScript mirror. Models/config/mirror and structural validators implemented; engine/context-dependent invariants remain for later slices.
- [x] **T-0.4:** Pin compatible runtime/dependency versions, including native Windows asyncio and CPU/offline mode; document startup.
- [x] **T-0.5:** Portable startup, Linux/Windows CI configuration, isolated offline CLI smoke, Python typechecking, MIME-derived download names and early upload authorization. Remote CI execution remains unverified.

## Phase 1: Evidence, ingestion and reproducible inputs

- [x] **T-1.1:** Build exact raw capture and capture manifest, immutable canonical serializer, media-byte store and distinct SHA-256 domains.
- [x] **T-1.2:** Implement append-only chained audit, content-addressed repository, deduplication and late media enrichment.
- [ ] **T-1.3:** Generate baseline/spliced JPEG byte fixtures with separate evaluation masks; no analytical outputs in fixtures.
- [ ] **T-1.4:** Build three replay scenarios with repeated waves, missing metadata, stable actor identities and optional historical baseline events.
- [ ] **T-1.5:** Add event-time replay clock, generation-safe reset and separate origin/scope stores.
- [ ] **T-1.6 (optional live):** Public Reddit feed adapter; Telegram preview adapter if accessible, with allowlist/backoff and graceful 403/429.

## Phase 2: Narrative and coordination analytics

- [ ] **T-2.1:** Versioned multilingual embedder and frozen TF-IDF fallback, separate vector indexes and 24-hour clustering.
- [ ] **T-2.2:** Typed claim registry, source snapshots, candidate retrieval and human contextual review/audit; reject synthetic cross-origin verification.
- [ ] **T-2.3:** Explainable multilingual lexicon harm indicators with supported-language coverage.
- [ ] **T-2.4:** Content-linked disjoint event pairing, repeated buckets, q_uv normalization and account/campaign synchronization.
- [ ] **T-2.5:** Explicit bot feature scaling, availability weights, additive contributions and null/sufficiency rules.
- [ ] **T-2.6:** Descriptive burst index and explicit UNSUPPORTED Hawkes fields; no proxy-to-Hawkes relabeling.

## Phase 3: Graph, media and geography

- [ ] **T-3.1:** Separate directed interactions and undirected sync projection, deterministic Louvain/centrality and platform-qualified IDs.
- [ ] **T-3.2:** Role precedence with temporal seed, bot/bridge/low-indicator eligibility and UNCLASSIFIED fallback.
- [ ] **T-3.3:** Real pHash/ELA report, bounding boxes, EXIF inspection and explicit C2PA/video/audio adapter states.
- [ ] **T-3.4:** H3 source/subject separation, profile uncertainty, coverage/sample gates and coordination-gated mismatch.
- [ ] **T-3.5:** Same-scope historical baselines with collection coverage, minimum buckets, origin separation and null Z without history.

## Phase 4: API, CTI and reporting

- [ ] **T-4.1:** Available-component CTI, effective weights, provisional tiers, eligibility gates, cooldown and rearm.
- [ ] **T-4.2:** FastAPI REST endpoints, typed async jobs, upload/artifact store, generation-safe mutations and safe error envelope.
- [ ] **T-4.3:** WebSocket sequence retention/resync, polling, snapshot revision consistency and session-scoped access.
- [ ] **T-4.4:** Integrity-verified ZIP exports containing dossier, HTML/PDF, manifest, STIX and authorized derivatives.
- [ ] **T-4.5:** Consistent organic/unclassified redaction across every representation; hash derivatives and omit restricted originals.
- [/] **T-4.6:** CORS, loopback defaults, upload size/type/dimension guards and reviewer identity from session. Local session/CORS/image guards implemented; claim-review integration and remaining media adapters pending.

## Phase 5: Complete investigation frontend

- [/] **T-5.1:** Next.js/Tailwind app shell, telemetry, campaign feed, origin/window badges and responsive layout. Foundation shell and live health implemented; analytical campaign feed/window/origin rendering pending.
- [ ] **T-5.2:** Canvas graph, sync/role/time controls, hulls, cascade lens, accessible node list and account/edge drawers.
- [ ] **T-5.3:** H3 map/arcs with offline outline, source-confidence composition, sample/coverage gates and baseline explanations.
- [ ] **T-5.4:** Cross-filtered propagation timeline with coordinated, low-indicator and unclassified volume and alert markers.
- [ ] **T-5.5:** Computed media comparison slider, pHash/hash details, EXIF/C2PA status and unsupported/error states.
- [ ] **T-5.6:** Candidate reference/claim review UI with synthetic warnings and authenticated reviewer action.
- [ ] **T-5.7:** Scenario controls, queued injection/upload flow, replay speed/time cursor, reset and reconnect/resync.
- [ ] **T-5.8:** Export format/privacy dialog, verification/job states and completed artifact downloads.
- [ ] **T-5.9:** Keyboard accessibility, reduced motion, multilingual typography, empty/loading/failure and narrow-screen states.

## Phase 6: Tests, evaluation and release

- [/] **T-6.1:** Schema/invariant tests, canonical serializer golden vectors, raw/canonical/media/audit corruption and export-failure tests. Foundation tests implemented; export-failure and engine-dependent cases pending.
- [ ] **T-6.2:** Coordination deduplication, same timestamps, 60s boundaries, event reuse, repeated buckets and benign coordination false positives.
- [ ] **T-6.3:** All-missing bot features, coverage boundaries, unclassified/organic/seed precedence and centrality edge cases.
- [ ] **T-6.4:** Media malformed/unsupported states, real ELA/pHash, missing provenance and no fixture score leakage.
- [ ] **T-6.5:** Geography zero denominators, source counts/coverage, no-baseline Z, matching scope and failed alert gates.
- [ ] **T-6.6:** CTI weights/coverage, no-media versus failed-media, tier boundaries, suppressed critical tier, cooldown and replay clock.
- [ ] **T-6.7:** Registry review, synthetic isolation, job lifecycle, auth/error envelopes, reset races and WebSocket recovery.
- [ ] **T-6.8:** Holdout evaluation with disjoint accounts/templates/families/seeds; report per-mode/language F1 and false positives.
- [ ] **T-6.9:** Backend pytest/Ruff, frontend typecheck/build and end-to-end scenario/injection/review/export journeys.
- [ ] **T-6.10:** Visual QA of graph/map/media/timeline, multilingual PDF, redaction and offline/narrow-screen views.
- [ ] **T-6.11:** Record measured performance, parameter/model/data hashes, known limitations and reproducible startup in memory/README.
- [ ] **T-6.12:** Release review: every mandatory task complete or explicitly reported unmet; optional adapters do not block offline acceptance.
