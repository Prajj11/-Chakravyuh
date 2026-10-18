# Implementation Plan: Chakravyuh

**Contract version:** 2.1.0  
**Updated:** October 18, 2026  
**Strategy:** Testable vertical slices; docs are complete, application scaffolding remains pending.

Use [tasks-v2.md](tasks-v2.md) for checkboxes, [backendschema-v2.md](backendschema-v2.md) for types/API and [trd-v2.md](trd-v2.md) for all algorithms. This plan does not override formulas or promise specific scenario CTI values.

## Sprint 1: Runtime, contracts and evidence foundation

Maps to Phase 0 and the evidence portion of Phase 1.
- Initialize backend/frontend/sample_data structure; lock compatible Python/frontend packages and document Windows startup.
- Implement schemas, enums, cross-field validators, configuration and parameter_set_id. Add TypeScript mirrors.
- Build canonical-json-v1 with golden serialization vectors. Store original payloads, canonical event bytes, raw capture manifests and media bytes using separate hashes.
- Implement immutable evidence references, append-only audit chain, idempotent ingestion, SQLite repositories and analytical-run lineage.
- Establish session identity, loopback/CORS configuration, typed errors and safe upload/artifact handling.

Exit: raw input can be retained, normalized, verified and retrieved; evidence mutation is detected; no model output is needed to test ingestion.

## Sprint 2: Raw replay and narrative analytics

Maps to remaining Phase 1 and NLP/claims in Phase 2.

Simulator emits raw platform-shaped objects and real media bytes. The normalizer assigns hashes and models. Evaluation labels/masks live in a separate test-only manifest inaccessible to analytical services. Use seed=42 by default and disjoint seeds/accounts/templates in evaluation.

| Scenario | Raw inputs and coverage |
|---|---|
| cmp_electoral_01 | 1 initial author, 18 rapid amplifiers with 4-18s offsets, 2 later bridge candidates and 15 slower participants; at least three waves starting 90s apart so repeated matching and >=180s account history can be evaluated; ~25% missing creation/location fields; real baseline and spliced JPEG bytes |
| cmp_geo_astroturf_02 | 1 initial author plus 14 repeated English/Hinglish amplifiers, >=3 waves; around 80% of known declared/GPS source cells external to the target; >=10 known-source events from >=5 authors; raw historical events for a matching topic/cell/collector scope if spike demonstration is enabled |
| cmp_organic_03 | 25 participants with >=3 spaced events each, >=180s observed spans, varied creation dates and unrelated natural discussion; no qualifying repeated co-post relationships; unmodified baseline image |
| Evaluation-only benign controls | Coordinated civic mobilization, legitimate scheduled announcements, organic viral discussion, same-time unrelated content, unavailable metadata and insufficient samples |

Never assert the above fixture descriptions equal predicted roles. Earliest observed seed is calculated from chronology; bots/bridges/organic eligibility are calculated from observed behavior. Missing metadata can leave participants UNCLASSIFIED.

Historical baseline demo: generate >=168 valid hourly source-event buckets in the prior 30 days, with collection-coverage records; compute counts/means/std at runtime. Use a stable versioned topic dictionary and separate SYNTHETIC_REPLAY storage. Never insert desired Z, baseline mean, bot score, CTI or deepfake confidence. Replay speed changes wall-clock duration but not event-time differences.

Implement fixed multilingual embedder or frozen TF-IDF fallback, 24-hour narrative assignment and harm registry. Add typed known_claims_registry.json and source snapshots. Synthetic references are clearly named synthetic demo advisories with no invented official URLs. Retrieval alone stays UNVERIFIED.

Exit: deterministic raw replay clusters dynamically, preserves origin and evidence, and produces candidate claim references without automatic truth judgments.

## Sprint 3: Coordination and graph investigation

Maps to coordination in Phase 2 and graph in Phase 3.
- Implement content linkage, disjoint pair matching, inclusive time windows, repeated buckets and q_uv normalization.
- Implement account/campaign sync sufficiency, descriptive burst index and explicit unsupported Hawkes fields.
- Implement all five scaled bot features, weighted coverage, null handling and additive contributions.
- Build directed interaction and undirected sync graphs; compute Louvain, centrality and role precedence including UNCLASSIFIED.
- Retain matched event IDs, observation spans and exact deltas for the drawer/edge inspector.

Exit: meaningful tests distinguish repeated coordinated patterns, benign coordination, uncoordinated discussion and insufficient observations. No hardcoded account IDs determine expected analytical roles.

## Sprint 4: Real image indicators and geographic uncertainty

Maps to remaining Phase 3.
- Calculate image-byte hashes, pHash candidates, JPEG ELA scale and normalized regions using actual pixels. Use a test-only manipulation mask for localization evaluation.
- Report EXIF presence and truthful C2PA adapter status. Video/audio without adapters remains UNSUPPORTED; no fixture telemetry enters reports.
- Resolve GPS/declared source geography separately from subject mentions. Implement same-resolution H3 comparison, scoped baselines, coverage, counts and null Z for missing history.
- Implement separate regional-spike and coordination-gated mismatch indicators.

Exit: computed artifacts are inspectable, missing data is represented explicitly and test fixtures cannot supply expected output scores.

## Sprint 5: CTI, API, jobs and export

Maps to Phase 4.
- Implement available-component CTI, effective weights, numeric tiers, alert gates, cooldown and rearm.
- Expose every endpoint from the backend contract. Queue heavy mutations; return JobAccepted, expose typed result polling, sequence WebSocket events and coherent snapshot revisions.
- Serialize reset/injection mutations with generation checks; isolate public/injected/replay origins.
- Implement authenticated contextual claim review and append-only review audit.
- Generate verified redacted investigative packages, including escaped HTML, multilingual PDF, valid STIX, dossier JSON, manifests and authorized derivatives.

Exit: a raw event can traverse the same pipeline into a campaign snapshot and a verified local export; failed integrity checks block export, and unsupported adapters cannot generate scores.

## Sprint 6: Complete command center

Maps to Phase 5.
- Build the responsive shell/feed, separate coordination/media/claim assessments, CTI coverage and origin/window badges.
- Add Canvas graph, role/sync/time filters, community hulls, cascade lens, accessible list and account/edge drawer.
- Add H3 map/arcs with offline fallback and sample/baseline/coverage explanations.
- Add timeline series, original-vs-ELA inspection and provenance details.
- Add claims review, scenario/injection/upload job controls, reconnect/resync, privacy/export dialog and artifact download.
- Verify common snapshot_revision across cross-filtered panels; handle null, insufficient, unsupported, failure and empty states.

Exit: complete keyboard-accessible investigation journey using calculated results; all frontend tasks remain pending until implemented and checked.

## Sprint 7: Evaluation and demonstration release

Maps to Phase 6.
- Run focused engine and API tests, backend lint, frontend typecheck/build and end-to-end journeys.
- Evaluate frozen settings on held-out families/accounts/templates/seeds. Report false positives and fallback/model results separately; accuracy targets are not assumed achieved.
- Verify corruption blocking, redaction leakage, synthetic reference isolation, coverage/tier boundaries, concurrent reset and WebSocket recovery.
- Inspect multilingual PDFs and graph/map/media/timeline layouts, offline behavior and narrow screens.
- Record actual dataset/model/config hashes, measured hardware/performance, limitations and startup commands in release docs.

Exit: all mandatory backlog items complete or explicitly reported unmet. Optional live connectors, fitted Hawkes, production infrastructure and validated video/audio models are tracked separately and do not silently become claimed capabilities.
