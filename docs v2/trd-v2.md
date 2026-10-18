# Technical Requirements: Chakravyuh

**Contract version:** 2.1.0  
**Updated:** October 18, 2026  
**Status:** Algorithms to implement and evaluate; all numerical cutoffs below are configurable MVP defaults, not calibrated probabilities.

This file owns algorithms and configuration. [backendschema-v2.md](backendschema-v2.md) owns wire models; [rules-v2.md](rules-v2.md) owns engineering and OSINT constraints.

## 1. Runtime and execution scope

| Area | MVP choice | Optional extension |
|---|---|---|
| Runtime | Python 3.11+, FastAPI, Uvicorn, Pydantic v2, pydantic-settings | Docker services |
| Queue/storage | asyncio.Queue, worker executor, SQLite, content-addressed local evidence files | Redis, PostgreSQL |
| NLP | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, 384 dimensions, when cached | New models only with recorded revisions and recalibration |
| Offline NLP | word/character TF-IDF + cosine; optional SVD fitted on training corpus | Does not promise cross-language semantic equivalence |
| Numeric/graph | NumPy, SciPy, scikit-learn, NetworkX Louvain seed=42 | Qdrant, Neo4j |
| Image analysis | Pillow, OpenCV, imagehash | C2PA validation adapter, separately evaluated image/video models |
| Geography | h3 major version 4 API, local gazetteer | Broader geocoder/NER adapters |
| Reporting | ReportLab PDF, escaped HTML, stix2 validation | External signed/anchored manifests |
| Frontend | Next.js App Router, React, strict TypeScript, Tailwind, Lucide | Radix primitives |
| Visuals | d3-force with Canvas; Deck.gl/MapLibre; Recharts | Provider-backed map tiles |
| Checks | pytest, Ruff, TypeScript typecheck, frontend production build | Recorded hardware-specific load tests |

Select and lock mutually compatible exact dependency versions during scaffolding. These are project constraints, not claims of latest releases. Support Windows without uvloop; native asyncio is the default. Cloud services, GPU, map tokens, and downloaded model weights are unnecessary for the offline acceptance path. Serve a bundled outline/coordinate grid when map tiles are unavailable.

NLP uses MODEL_INFERENCE only for a loaded versioned model, HEURISTIC_INDICATOR for TF-IDF and lexicons. ELA uses COMPUTED_ELA_PHASH; structural calculations use COMPUTED_PIPELINE. SIMULATED_FIXTURE_METADATA is reserved for non-scoring test annotations. Never load arbitrary checkpoints from upload payloads. Video/audio inference is an optional adapter; absent or unevaluated adapters return UNSUPPORTED, not a made-up score. Loading weights alone never establishes validated deepfake detection.

## 2. Canonical constants and units

Implement these defaults centrally in backend/app/config.py; record the full parameter set and its hash with every run. Counts and ratios use deduplicated observed events, never simulator role labels.

| Constant | Default |
|---|---|
| SEMANTIC_CLUSTER_SIMILARITY | 0.85 |
| NARRATIVE_WINDOW_HOURS | 24 |
| TEMPORAL_CO_POST_WINDOW_SEC | 60.0, inclusive |
| TEMPORAL_DECAY_TAU_SEC | 20.0 |
| SYNC_MIN_DISTINCT_BUCKETS | 2 |
| ANALYSIS_MIN_OBSERVATION_SEC | 180 |
| ANALYSIS_MIN_ACCOUNT_POSTS | 3 |
| COORDINATION_MIN_AUTHORS | 3 |
| BOT_PROBABILITY_HIGH_CUTOFF | 70.0 (legacy config name; output is bot_indicator_score) |
| BOT_SYNC_SCORE_CUTOFF | 0.65 |
| ORGANIC_BOT_MAX_EXCLUSIVE | 50.0 |
| ORGANIC_SYNC_MAX_EXCLUSIVE | 0.45 |
| BOT_MIN_FEATURE_COVERAGE | 0.30 |
| ORGANIC_MIN_FEATURE_COVERAGE | 0.60 |
| GEO_H3_RESOLUTION | 5 |
| GEO_Z_SCORE_SPIKE_THRESHOLD | 3.0 |
| GEO_BASELINE_LOOKBACK_DAYS | 30 |
| GEO_BASELINE_MIN_HOURLY_BUCKETS | 168 |
| GEO_MIN_SOURCE_COVERAGE | 0.30 |
| GEO_MIN_KNOWN_SOURCE_POSTS | 10 |
| GEO_MIN_KNOWN_SOURCE_ACCOUNTS | 5 |
| ASTROTURFING_MISMATCH_RATIO | 0.60 |
| CTI_MIN_COMPONENT_COVERAGE | 0.60 |
| CTI_MIN_SCORED_POST_COVERAGE | 0.30 |
| CTI_CRITICAL_ALERT_THRESHOLD | 75.0 |
| ALERT_MIN_CAMPAIGN_POSTS / ALERT_MIN_CAMPAIGN_AUTHORS | 10 / 5 |
| ALERT_COOLDOWN_SEC | 300 |
| CLAIM_CANDIDATE_SIMILARITY | 0.85 (retrieval only) |

Use these severity intervals on the unrounded CTI (100 is included in the final tier): LOW [0,40), MEDIUM [40,60), HIGH [60,75), CRITICAL [75,100]. A null CTI has no tier and displays INSUFFICIENT DATA. LOW describes the observed composite score, not proven organic behavior.

## 3. Exact-byte evidence and canonicalization

1. Capture the original HTTP response entity bytes before parsing; retain source URL, content type, collector scope, platform event key, capture format, and collection time. If a feed response holds multiple posts, store one response blob and a per-event source key/pointer in the raw capture manifest. Hash the exact retained entity bytes as raw_payload_sha256.
2. For replay/injection, serialize the unnormalized source object once with canonical-json-v1, retain those bytes, and mark raw_capture_format=CANONICAL_JSON_V1. They are synthetic/user-supplied input, never claimed as original platform responses.
3. Store media as exact bytes with a separate SHA-256; pHash is a similarity feature only. Fetch failure stays UNAVAILABLE. Never substitute a URL string or pHash for the media-byte hash.
4. Normalize to UnifiedSocialEvent. Normalize timestamps to UTC, preserve original text and URL lists in the event; use separate cleaned copies for NLP and URL matching. Serialize the entire initial model excluding only canonical_event_sha256, then hash those bytes as canonical_event_sha256. Store the same serialized bytes. No campaign ID, pHash, model score, or mutable membership enters the event.
5. canonical-json-v1 uses UTF-8 without BOM, sorted object keys, compact separators, ensure_ascii=False, allow_nan=False, preserved array order, enum values, explicit nulls/default fields, and UTC timestamps with six fractional digits followed by Z. Do not Unicode-normalize, trim text, or reorder arrays for evidence. This is the project's defined serializer, not a claim of RFC canonicalization. Pin serializer tests across supported runtimes.
6. Evidence refs resolve server-side to content-addressed files. Never overwrite a hash-addressed file. Treat nested models/containers as immutable even when a framework only freezes attributes. Later account snapshots, media fetches, geography corrections, campaign reassignment, and scores create append-only enrichment records.
7. Audit entries serialize with the same serializer excluding entry_sha256; hash that serialization, including previous_entry_sha256. First previous hash is null. Serialize concurrent appends. Record actor, action, UTC time, input/artifact hashes, version, parameter set, and origin.
8. Before export rehash retained raw, canonical, media and analysis artifacts and walk audit links. Corruption fails export. Missing items are explicit unavailable entries. A chain of local hashes detects changes relative to its retained manifest; external trusted timestamps/signatures and resistance to wholesale privileged rewriting are outside MVP.

## 4. Narrative clustering, claim references and harm indicators

- Preprocess a separate text copy: Unicode normalization, case-folding, whitespace cleanup, tracking-parameter removal for match URLs, and a versioned English/Hindi/Hinglish alias dictionary. Never alter evidence text.
- Fit TF-IDF/SVD vocabulary on training/baseline corpus only; freeze it for a run. Record corpus hash, dimensions and revision. Zero vectors cannot match and create an unassigned/new cluster with a reason. Never compare embeddings from different revisions or modes; rebuild indexes when changing embedder.
- Within the last 24 event-time hours, assign a unit vector to its highest-cosine centroid if similarity >=0.85; ties use lexical campaign ID. Update centroid as normalized arithmetic mean of member vectors. Otherwise create a stable deterministic cluster ID. Late events inside the window recompute affected snapshots; older events remain searchable evidence without rewriting closed alerts.
- A fixed similarity threshold is an initial setting to evaluate separately for model and fallback modes. Synthetic phrase overlap is not evidence of general multilingual accuracy.

known_claims_registry.json contains ClaimReference records from the backend schema and retained source snapshots. Retrieval returns candidates at similarity >=0.85. Similar wording does not establish that a source addresses the same claim, date, location, actor, or media. Keep UNVERIFIED until a human reviewer confirms context and records the reference, reviewer identity, note and time through the claim-review endpoint. Stale/conflicting references stay UNVERIFIED with reasons; CONTEXT_MISSING is a reviewed finding. Synthetic references have synthetic_reference=true, local snapshot refs, and titles beginning "Synthetic demo advisory"; no invented official URLs or real-agency endorsements. They may only be reviewed against synthetic replay campaigns.

The harm fallback uses a versioned registry of normalized phrases with category and integer severity 0-100. Per post take the maximum severity of exact normalized phrase matches; campaign harm is the mean over supported-language posts. No match returns 0 only for supported languages; unsupported language returns unavailable. Require supported-language coverage >=0.30 for the campaign component. Display as a lexicon indicator, with matched spans and quotation/context caveats, not established intent or a calibrated toxicity probability.

## 5. Coordination normalization and bot indicators

### 5.1 Event matching and synchronization

Use event-time UTC in the active 24-hour narrative window. Exclude duplicate event IDs and same-author pairs. Require same narrative plus at least one shared normalized URL, identical collected media-byte hash / qualifying pHash candidate, or text cosine >=0.85. A shared hashtag alone never qualifies.

For each unordered account pair, sort qualifying event pairs by (absolute time delta, earlier event time, event IDs). Greedily select disjoint pairs so an event is used at most once for that account pair. Accept 0 <= delta <=60 seconds, including simultaneous distinct-author posts. Bucket matches by floor(earlier_event_epoch_seconds/60). Require matches in at least two distinct buckets; this rejects a single coincident burst as sufficient pair evidence.

For selected matches, w_uv=sum(exp(-delta/20)); normalized edge q_uv=1-exp(-w_uv). A non-eligible pair has no synchronization edge. Store matched event IDs and deltas so the edge is reproducible.

For an account observed for >=180 seconds with >=3 campaign posts, sync_score is the arithmetic mean of its five highest eligible q_uv values (or all if fewer than five). No eligible peers gives 0; insufficient history gives null. Account coverage is observed_span/180 capped at 1, additionally gated by post count. Matched-peer contributions are q_uv divided by the number averaged and sum to the account score.

Build an undirected sync graph; connected components with >=3 authors and mean eligible edge q_uv >=0.65 are candidate coordinated groups. Campaign sync_score is the maximum mean edge q_uv among all components with >=3 authors, including components below 0.65. A sufficiently observed campaign (>=180 seconds, >=3 authors and >=10 posts) with no component of >=3 authors has score 0; an insufficiently observed campaign has null. Expose coordinated-account count, eligible-pair count, and the fraction of authors with available account sync. Campaign sync contributions are the edge q_uv values divided by edge count in the selected component (ties by sorted account IDs), and sum to its score. High synchrony remains an indicator; it does not prove automation, intent, or falsity.

### 5.2 Burst index and optional Hawkes fitting

Aggregate one-minute event-time counts. With >=10 completed minute bins and at least 20 events, burst_index=sample_variance(counts)/max(mean(counts),1). Otherwise null. This is a descriptive dispersion index; never relabel it a Hawkes branching ratio or use it alone to classify orchestration.

Hawkes fitting is deferred from MVP. hawkes_status=UNSUPPORTED and hawkes_branching_ratio=null until a separately versioned estimator specifies fitting window, likelihood, optimizer, convergence tests, stationarity constraints, minimum sample and calibration tests. Burst index alone does not enter CTI.

### 5.3 Explicit bot-feature scaling

Each f is in [0,100]. "Available" means its evidence prerequisites are met.

| Feature | Base weight | Definition / prerequisite |
|---|---|---|
| sync_tightness | 0.35 | 100 * available account sync_score |
| creation_batch_density | 0.25 | 100 * min(other active authors created within +/-48h of this author / 10, 1); own creation date and >=3 other known creation dates required |
| amplification_ratio | 0.20 | 100 * repost/quote/qualifying repeated-copy event count / account event count; >=3 events; count each event once |
| posting_rate_burst | 0.10 | 100 * clip((observed hourly rate / max(baseline hourly rate,1) - 1)/9,0,1); >=180s account span, >=3 events and >=168 valid historical hourly baseline buckets required |
| handle_entropy | 0.10 | 100 * min(trailing digit count / 6,1); nonempty handle; explicitly a weak lexical heuristic, not an identity inference |

For available-feature mask m and weights omega:
coverage=sum(m*omega); B=sum(m*omega*f)/coverage.
If coverage <0.30, <3 observed account posts, or account span <180 seconds, B=null and status=INSUFFICIENT_DATA. All-missing has coverage=0 and null score. Otherwise feature_contributions[k]=m_k*omega_k*f_k/coverage and sums to B. Unavailable features are omitted from effective weights and named in missing_signals. Use only observed account records, never simulator roles. B is bot_indicator_score, not a calibrated probability; do not call heuristic contributions SHAP.

## 6. Graph construction and role precedence

Account IDs are platform-qualified; never automatically merge matching handles across platforms. Keep a directed interaction graph and a separate undirected synchronization projection. A repost/quote edge points from the referenced source account to the amplifying account; replies point from parent to replying account. Missing parent identities remain unresolved rather than invented. Cascade out-degree counts only source-to-amplifier edges, excluding synthetic bidirectional sync edges.

Run Louvain on the undirected weighted projection of interactions plus q_uv sync edges, resolution=1.0, seed=42. Sum parallel contributions for community detection; retain edge types separately in output. Compute normalized betweenness on the interaction projection; empty/single-node graphs have centrality 0 and deterministic communities.

The release uses NetworkX 3.5 Louvain and Rustworkx 0.17.1 exact sequential directed Brandes betweenness (normalized, endpoints excluded). Deterministic node/edge ordering and sequential accumulation preserve reproducibility. Random-graph parity tests compare against NetworkX exact centrality to absolute tolerance 1e-12. This is an equivalent execution backend, not sampled centrality or a changed role threshold. Implementation versions are retained in the method bundle.

Assign one primary role in this order:

1. EARLIEST_OBSERVED_SEED: earliest observed author in the campaign; ties by platform-qualified account ID. No out-degree cutoff may replace an earlier author with a later popular one. Display cascade reach separately. This role is observational and does not imply suspiciousness.
2. BOT_AMPLIFIER: available B>=70 and available account sync>=0.65.
3. BRIDGE_INFLUENCER: positive betweenness >=85th percentile, and at least two interaction edges connecting a candidate coordinated group to a low-indicator community. Determine low-indicator eligibility from step 4 before applying role precedence; a community qualifies when a majority of its sufficiently scored members meet that eligibility.
4. ORGANIC_USER: available B<50, sync<0.45, bot feature coverage>=0.60, >=3 events, and >=180 seconds account span. UI label is "Low observed indicators"; this role is not a guarantee of authenticity.
5. UNCLASSIFIED: all remaining accounts, including missing evidence, conflicting indicators, and intermediate scores. Include the reason.

Earliest seed may be null only for an empty campaign. Organic and unclassified handles are anonymized by default in exports.

Timeline bins partition every campaign event exactly once: authors in candidate coordinated groups contribute coordinated_volume; remaining authors satisfying low-indicator eligibility contribute low_indicator_volume; all others contribute unclassified_volume. Use underlying evidence eligibility rather than primary role so the temporal seed is not arbitrarily omitted. Record the snapshot revision; later evidence may change historical classifications in a new snapshot, without changing original events.

## 7. Image forensics and provenance

Compute SHA-256 from exact media bytes before processing. For supported images, compute 64-bit DCT pHash; Hamming distance <=10 returns candidate related-media matches, not a guarantee of cropping invariance or manipulation. Exclude self-matches.

For ELA, decode to RGB, recompress to JPEG quality 90, and compute grayscale absolute RGB difference D using the channel mean. Display min(255,15*D). Define p50 and p95 on unamplified D and ela_anomaly_score=100*clip((p95-p50)/(10*max(p50,1)),0,1). This is a configured anomaly scale requiring evaluation, not a calibrated manipulation probability. Threshold D at max(15,p95), extract 8-connected components of >=16 pixels, merge overlapping boxes, and return normalized boxes/intensity. Empty regions are valid. manipulation_indicator_score equals ELA score in MVP; report COMPUTED_ELA_PHASH and ELA-only limitations.

Missing EXIF is exif_present=false, not proof of stripping. C2PA defaults NOT_CHECKED or UNSUPPORTED; MISSING requires an adapter inspection and VALID requires cryptographic verification. Invalid/missing provenance does not add a manipulation penalty. A validated manifest does not by itself establish camera origin or claim truth.

Video/audio without the relevant adapter have UNSUPPORTED, null model scores, and no fabricated lip-sync results. Optional keyframe image results must be explicitly frame-level, with model revision, sampling policy, and calibration ID when calibrated. Never aggregate ELA into a claimed video deepfake probability. SIMULATED_FIXTURE_METADATA cannot contribute to any forensic score.

## 8. Geographic baseline, coverage and alerts

Author sources come only from explicit GPS or a resolvable declared profile. Treat declared profiles as declarations, not physical-location proof. Subject mentions come from the gazetteer; ambiguity stays unresolved. Use H3 resolution 5 for all mismatch comparisons; resolution 7 may be a separately recomputed display layer, never mixed into the same denominator.

For each campaign's target cell at watermark T, collect campaign posts with that target in (T-3600 seconds,T]. N_total is that set, exposed as target_campaign_posts_1hr; N_known includes only GPS/resolved profile authors. Coverage=N_known/N_total, or 0 if N_total=0. GMR=external_known/N_known, or null when N_known=0. External means source cell is outside the target's grid_disk radius 2. If grid-distance evaluation fails, membership in grid_disk is authoritative. Sample gates also require >=10 known-source posts from >=5 distinct authors. Record window_end_utc=T.

A regional baseline is keyed by origin, collector scope, target H3 cell/resolution, and a stable topic-family ID from the versioned topic dictionary. The report records baseline_scope_id. current_velocity_1hr is current target/topic-family volume across narratives in (T-3600 seconds,T], and is distinct from target_campaign_posts_1hr used for source coverage. Compare it to historical hourly volume in the exact same scope. Do not compare one campaign's count against unrelated platform-wide volume. If topic family is unresolved, baseline status is INSUFFICIENT_DATA; never choose a convenient history scope.

Use the last 30 days excluding the current trailing hour; include zero-count hours only when collector coverage >=0.90 is recorded. Require >=168 valid hourly buckets. Mean and sample standard deviation give Z=(current-mean)/max(std,1). Otherwise baseline_status=INSUFFICIENT_DATA and Z=null. Historical replay events may create synthetic baselines but must carry SYNTHETIC_REPLAY origin and remain separate from public/user data. Never insert desired baseline means or Z-scores.

A geographic astroturfing indicator fires only when ALL hold:
- GMR>=0.60;
- source coverage>=0.30;
- >=10 known-source posts and >=5 known-source authors;
- available campaign sync_score>=0.65.

A regional spike separately requires valid baseline and Z>=3.0. A mismatch alert can exist without a spike; clearly distinguish the two. This alert is an investigation indicator, not proof that external actors or foreign jurisdictions are responsible.

Geo CTI component is max(100*clip(max(Z,0)/6,0,1) when Z exists, 100*GMR when all mismatch alert gates pass). If neither input is available, it is null; a valid baseline with no spike can yield a measured zero. Report coverage and sample gates beside every map value.

## 9. Composite CTI and early-warning eligibility

Base weights: sync 0.30; bot_density 0.25; media_forensics 0.20; geo_anomaly 0.15; harm_severity 0.10.

| Component | Definition and availability |
|---|---|
| sync | 100 * available campaign sync_score |
| bot_density | 100 * posts from B>=70 authors / all posts from sufficiently scored authors; available only if scored-post coverage>=0.30 and >=3 scored authors |
| media_forensics | Maximum available manipulation_indicator_score from real computed/inferred media reports; no media is a known 0; pending/failed/unsupported-only media is null |
| geo_anomaly | Section 8 component, or null |
| harm_severity | Section 4 supported-language indicator, or null |

For mask m, CTI coverage=sum(base_weight*m). Effective weight=base_weight/coverage for available components; CTI=sum(effective_weight*component). Do not replace unavailable components with zero. If coverage=0 or sync is unavailable, CTI=null with INSUFFICIENT_DATA. Otherwise publish the provisional computed score and its tier, even when coverage is low, alongside missing signals and suppression reasons. Feature contributions are weighted component values and sum to CTI. A computed composite retains input component_modes; it never disguises heuristic components as model probabilities.

A CRITICAL-tier score triggers a CTI_ALERT only when score>=75, CTI coverage>=0.60, campaign sync>=0.65, scored-post coverage>=0.30, >=10 campaign posts, and >=5 campaign authors. Otherwise show its numeric tier plus "Alert suppressed: insufficient evidence" and reasons. This prevents a single isolated media/keyword score from creating a coordinated-campaign warning.

Emit once on an eligible below-to-above transition while armed; suppress repeated same-campaign alerts for 300 event-time seconds. After firing, rearm only after CTI<70 for 120 consecutive event-time seconds; the next alert also requires cooldown expiry and a new qualifying transition. Initial unavailable-to-eligible observation counts as the first transition. In replay, event-time controls analysis, cooldowns, and simulation speed; collection timestamps retain actual wall-clock capture time. A state reset uses a new generation and clears replay alert state only.

UI/WebSocket alerts are automatic local notifications. External incident webhooks and official submission are outside MVP and require a reviewed, explicit human dispatch step if later implemented.

## 10. Evaluation and acceptance

- Split train/calibration/test by scenario family and account/template sets, with disjoint seeds. Freeze thresholds on calibration before test; never tune against test outputs. Record dataset hashes, fallback/model mode, missing rates and parameter versions.
- Include coordinated benign emergency mobilization, ordinary viral posts, repeated legitimate scheduled announcements, near-simultaneous unique content, profile-location uncertainty, unsupported media and damaged files. Report false positives, not just attack detection.
- Coordination F1>=0.85 on held-out synthetic/replay campaigns is a target, not an achieved metric or production claim. Report per-mode/per-language results and uncertainty. ELA box IoU>=0.70 is an exploratory synthetic-localization target; failure is reported rather than hidden.
- Tests cover empty/single-node graphs, zero available features, exact timestamps, 60-second boundaries, event reuse prevention, 0.65/70/75 boundaries, redaction leaks, hash corruption, synthetic reference isolation, failed models, zero known geography and missing baselines.
- Offline demo must support all three scenarios, injection, map/graph/timeline cross-filtering, claim review, reconnect, and verified redacted ZIP/PDF/STIX export. Outputs are measured; no expected scenario CTI is hardcoded.
- Initial performance targets: read P95<200ms; scoring <2s for a declared 100-event text/image batch excluding queued heavy inference; 1,000-node local graph recalculation <800ms; export <2s for 100 events. Record hardware, data size and cold/warm conditions. Queued endpoints return promptly. Larger 5,000-node rendering and 500 events/sec remain measured stretch goals, not MVP guarantees.

Implementation parameter revision 2.1.0.1 centralizes all algorithm constants from sections 4–9
(including feature scales, ELA, graph and sample gates) in Parameters. Defaults are unchanged.
The full canonical parameter JSON, including this revision, determines parameter_set_id.
Lexical preprocessing aliases are versioned with the frozen corpus hash in tfidf-v1.
