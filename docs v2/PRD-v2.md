# Product Requirements: Chakravyuh

**Contract version:** 2.1.0  
**Updated:** October 18, 2026  
**Status:** Ready for local MVP implementation; detection accuracy is not yet validated.

## 1. Purpose and scope

Chakravyuh is a local-first investigation workbench for public social content. It detects coordinated amplification indicators, media anomalies and geographic narrative patterns, and helps analysts inspect supporting evidence. Target users are cyber-cell investigators, threat-intelligence analysts and digital fact-checkers.

Three separate assessments are mandatory: **coordination**, **media integrity indicators**, and **claim verification**. A composite Campaign Threat Index (CTI) prioritizes review. It neither proves a claim false nor identifies a criminal actor.

The complete active contract is the ten files in docs v2, version 2.1.0; v1 is historical. [trd-v2.md](trd-v2.md) owns formulas/constants; [backendschema-v2.md](backendschema-v2.md) owns enums and API payloads. No source credentials or GPU are required for the offline acceptance path.

## 2. MVP and extension boundaries

| Deliver in MVP | Optional / deferred |
|---|---|
| Three reproducible scenarios, custom injection, local evidence storage | Broad cross-platform live coverage |
| Multilingual model when cached; explicitly limited TF-IDF fallback | Validated general cross-language accuracy |
| Repeated co-post analysis, explainable bot indicators, Louvain and propagation | Trained/calibrated bot classifier and Hawkes fitting |
| Real image pHash, ELA, EXIF inspection; explicit C2PA adapter status | Validated image/video/audio deepfake detectors |
| H3 map, location coverage, computed baselines when history exists | Guaranteed author physical location |
| Claim-reference retrieval plus human review | Automated truth judgments |
| Dashboard, local alerts, verified redacted HTML/PDF/STIX bundles | External dispatch/takedowns and legal-admissibility guarantees |
| Optional public Reddit feed adapter; Telegram preview adapter if accessible | X/YouTube/Instagram connectors pending access and implementation |

Public adapters are best-effort features; platform access failures must not block the replay demo.

## 3. Functional requirements

### FR-1: Ingestion, narrative clustering and claim context

- Preserve public-source raw payload bytes, source provenance, actual collection time, raw hash, media-byte hashes and a separate canonical-event hash.
- Normalize to the immutable flat UnifiedSocialEvent. Keep memberships and enrichment outside the event. Missing author metadata remains null.
- Cluster observed text in a 24-hour event-time window using versioned embeddings and initial cosine threshold 0.85. Keep model and fallback vectors separate.
- Retrieve candidate references from known_claims_registry.json; default claim status is UNVERIFIED.
- Allowed claim statuses are UNVERIFIED, CONTRADICTED_BY_SOURCE, CORROBORATED and CONTEXT_MISSING. Similarity alone never changes status; a reviewer records context, evidence, identity and time.
- Synthetic advisories remain visibly synthetic and cannot verify real injected/public claims.

### FR-2: Coordination and bot indicators

- Require content linkage and repeated matching across at least two minute buckets within inclusive 60-second co-post windows. A single simultaneous burst or shared hashtag is insufficient.
- Compute normalized pair/account/campaign sync scores using the TRD. Expose event IDs, observed deltas, repeated buckets and coverage.
- Compute bot_indicator_score on available features with exact additive contributions. Insufficient observations return null and reasons, not fabricated certainty.
- Supply a descriptive minute-count burst index. Hawkes estimates remain null/UNSUPPORTED until the optional estimator has a complete evaluated contract.

### FR-3: Media indicators

- Compute exact-byte SHA-256, 64-bit pHash candidates and real JPEG-recompression ELA maps on supported images.
- Expose manipulation_indicator_score as an anomaly scale, not a calibrated probability. Do not equate missing EXIF or C2PA with manipulation.
- C2PA reports NOT_CHECKED, MISSING, VALID, INVALID or UNSUPPORTED according to adapter behavior. Without video/audio adapters, return explicit UNSUPPORTED and null model/lip-sync scores.
- Tag every result with computation mode and input origin; never feed simulated telemetry into measured scores.

### FR-4: Graph and account roles

Construct separate interaction and sync projections, identify communities and compute centrality. Primary role precedence is:
1. EARLIEST_OBSERVED_SEED: earliest collected author, ties by ID; display collection limits and reach separately.
2. BOT_AMPLIFIER: available bot score >=70 and account sync >=0.65.
3. BRIDGE_INFLUENCER: qualifying positive betweenness and cross-community interactions under the TRD.
4. ORGANIC_USER: available bot score <50, sync <0.45, bot-feature coverage >=0.60 and sufficient observations; label "Low observed indicators."
5. UNCLASSIFIED: everything else.

Do not merge accounts across platforms from handle similarity. Role labels are observations/indicators, not identity or intent findings.

### FR-5: Geography with uncertainty

Separate GPS/declared author source from the place mentioned in text. Unknown or ambiguous sources stay unavailable; profile locations are declarations.

At H3 resolution 5, display regional velocity, source coverage, known-source author/post counts and GMR. An astroturfing indicator requires GMR>=0.60, source coverage>=0.30, >=10 known-source posts, >=5 known-source authors and campaign sync>=0.65.

A regional spike separately requires Z>=3 and >=168 valid hourly historical buckets in the same collector/topic/cell/origin scope from the preceding 30 days. Missing history means no Z-score. Synthetic baselines are computed from replay events and visibly labelled.

### FR-6: Workbench, warning and evidence export

- Dashboard supplies campaign feed, coordination graph, account drawer, geographic map/arcs, propagation timeline, media comparison and claim-reference review.
- CTI uses the TRD's weighted available components and exposes effective weights, input methods and missing evidence.
- Tiers use unrounded scores: LOW [0,40), MEDIUM [40,60), HIGH [60,75), CRITICAL [75,100].
- A score >=75 emits a local early warning only when coverage, coordination and sample gates pass. Provisional critical-tier scores show suppression reasons. Null scores show INSUFFICIENT DATA.
- Queue heavy work and expose typed jobs, polling and WebSocket notifications.
- Export verified tamper-evident ZIP packages containing HTML/PDF, STIX, manifest and authorized evidence/derivatives. Default redact organic and unclassified accounts throughout.
- Integrity mismatch blocks export; unknown/missing evidence is explicitly listed. Download is a local action; external incident submission is deferred.

## 4. Non-functional requirements and acceptance

The October 19 dataset extension adds 25 fictional source cases, 7,500 posts and 1,500 accounts across 25 cities, with English/Hindi/Hinglish variants, suspicious amplification patterns, benign mobilisation and ordinary discussion. Cases can be loaded individually or together from Scenario studio, with fast per-case analysis or timed replay. The original three acceptance scenarios remain available. Generator intentions must never become analytical scores or evaluated ground truth. New media references reuse explicitly synthetic image fixtures; no new video/audio inference or public-data collection is implied. See `sample_data/case_pack/README.md` for inventory, regeneration and limitations.

Follow [rules-v2.md](rules-v2.md) for public-only collection, session access, safe uploads, privacy, modularity, strict types, reproducibility and tests.

Targets, to be measured: REST read P95<200ms; text/image scoring <2s per declared 100-event batch excluding heavy queued inference; 1,000-node graph recalculation <800ms; 100-event export <2s. No unmeasured performance claim is part of delivery.

Coordination F1>=0.85 on held-out synthetic/replay splits is a target. Report benign-coordination false positives, missing-data behavior and model/fallback results separately. ELA localization has an exploratory IoU target, not a verified deepfake accuracy claim.

Acceptance requires an offline scenario/injection-to-investigation-to-redacted-export journey, all computed outputs, inspectable provenance, missing-data states, functioning reconnect and tests. Full frontend and release verification tasks are tracked in [tasks-v2.md](tasks-v2.md).
