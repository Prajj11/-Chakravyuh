# Application Flow and Investigation Journeys: Chakravyuh

**Contract version:** 2.1.0  
**Updated:** October 18, 2026

[backendschema-v2.md](backendschema-v2.md) defines payloads/endpoints; [trd-v2.md](trd-v2.md) defines score and alert gates. Values shown during a run must be computed, not copied from this document.

## 1. Background pipeline

1. Collector, replay or injector provides raw objects/bytes and declared origin. Retain original capture, manifest and exact media bytes.
2. Ingestion validates/normalizes and creates immutable UnifiedSocialEvent with raw and canonical hashes. Append INGEST audit entry; deduplicate by source identity.
3. NLP assigns a narrative from fixed embeddings, emits harm indicators and retrieves claim candidates. Candidate matches remain UNVERIFIED.
4. Coordination matches repeated content-linked account pairs across minute buckets, normalizes weights and computes missing-safe bot indicators.
5. Graph worker constructs interaction and sync projections, Louvain communities, centrality and primary roles including UNCLASSIFIED.
6. Geography resolves source declarations separately from subject mentions, computes coverage/mismatch and checks baseline availability.
7. Image worker calculates pHash/ELA from bytes; video/audio without adapters returns UNSUPPORTED.
8. Reporting publishes a coherent snapshot revision and CTI with available-component weights. Local alerts require both critical-tier score and every eligibility gate.
9. WebSocket emits typed messages and completed jobs. Failures surface scoped status and evidence reasons; they do not fabricate downstream scores.

Claim review is a separate human action. Later enrichment/reference review creates new analytical/audit records without modifying initial evidence.

## 2. Replay and injection

### Replay

Analyst chooses one of cmp_electoral_01, cmp_geo_astroturf_02, cmp_organic_03 or all, plus seed/speed. POST /api/v1/simulate/scenario returns 202 JobAccepted. Poll /api/v1/jobs/{job_id} until complete, then load campaign summaries/details. Do not assume the job response is already a campaign.

Replay supplies multiple waves and historical input events as specified in the implementation plan. Each event is captured by ingestion and all outcomes are calculated. SYNTHETIC_REPLAY remains visible across views and export. Collection wall-clock time and simulated event time are distinct.

Reset replaces the active replay generation; concurrent old-generation mutations fail/cancel visibly. Prior evidence is retained. CTI may differ across parameter sets and available evidence; the UI never guarantees a predetermined critical result.

### Injection

Upload optional images through POST /api/v1/media, receiving an artifact ID. Submit text, actor identity and optional timestamp/location/media IDs to POST /api/v1/events/inject. Defaults provide no invented source geography. Server assigns USER_INJECTED origin.

The queued job result contains UnifiedSocialEventEnriched with nested assessments and their coverage/reasons. A single injected post generally lacks enough history for bot/coordination conclusions; display insufficient data while retaining searchable evidence. Injected content never inherits synthetic references or baselines.

## 3. Triage and evidence inspection

A CTI_ALERT opens an eligible campaign snapshot. Investigator sees:
- collection window, origin, numeric CTI and contribution/coverage breakdown;
- separate coordination, media indicators and claim verification;
- missing/heuristic/model status and why an alert was or was not eligible.

Selecting graph sync threshold 0.65 filters the view. It does not recalculate account truth or delete weaker evidence. Edge inspection shows original event IDs/deltas and repeated buckets; node inspection opens the bot/sync dossier and role reasons. The earliest observed seed is dataset-bounded, while cascade reach is shown separately.

For a real emergency coordination pattern, synchrony may remain high while claim status is UNVERIFIED or reviewed CORROBORATED. No automatic "disinformation" verdict follows.

## 4. Geographic investigation

Selecting a target cell shows GMR, source coverage, known-source posts/authors and source declaration quality. A mismatch indicator requires GMR>=0.60, coverage>=0.30, at least 10 known-source posts from 5 authors and campaign sync>=0.65.

Inspect historical scope and valid bucket count separately. Z>=3 is a regional spike only with >=168 valid historical hourly buckets. Missing history shows unavailable; the map must not substitute a desired Z. Declared profile arcs do not claim measured physical location.

## 5. Media and claim verification

Media view requests completed ForensicMediaReport and compares original with computed ELA. Candidate related images display pHash distance and byte hashes. EXIF/C2PA status reflects actual inspection; missing metadata is not itself manipulation. An absent video/audio model yields UNSUPPORTED.

Claims tab presents retrieved source/snapshot and context. Reviewer checks subject, date, region and source relevance, then submits ClaimReviewRequest via PUT /api/v1/campaigns/{campaign_id}/claim-review. Server records reviewer identity/time and CLAIM_REVIEW audit. A candidate match alone cannot set CONTRADICTED_BY_SOURCE. Synthetic demo advisories are labelled and rejected for real/injected claims.

## 6. Export

1. Analyst opens export dialog, chooses bundle/PDF/HTML/STIX and redaction (default on).
2. POST /api/v1/campaigns/{campaign_id}/export returns 202 JobAccepted.
3. Worker verifies raw/canonical/media/artifact hashes and audit links. EVIDENCE_INTEGRITY_MISMATCH fails the job; missing source items remain explicitly unavailable.
4. Redact organic and unclassified accounts consistently, omit restricted originals and hash sanitized derivatives with original-hash linkage.
5. Produce ZIP with report formats, STIX, JSON dossier and manifest per contract. Poll job or receive JOB_UPDATED, then GET the session-protected artifact download URL.

An investigative package conveys evidence and uncertainty, not guaranteed truth or legal admissibility. Download does not dispatch an incident outside the application; external dispatch is deferred.

## 7. Recovery and UI consistency

Use job polling regardless of stream availability. On WebSocket disconnect, show reconnecting and poll REST every 3 seconds; backoff is 1/2/4/8 seconds capped at 30. Resume by last_sequence; expired history triggers SCENARIO_RESET and complete REST resync.

Use one snapshot_revision across campaign graph/map/timeline/drawer; discard stale responses after switching campaigns or resetting generation. Show scoped worker failure, unsupported adapters, no-baseline states and empty filters without hiding available evidence. Preserve keyboard focus when opening/closing panels and support reduced motion.
