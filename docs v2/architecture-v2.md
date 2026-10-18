# System Architecture: Chakravyuh

**Contract version:** 2.1.0  
**Updated:** October 18, 2026  
**Pattern:** Local-first event-time pipeline with immutable evidence and rebuildable analytical views.

## 1. Architecture and document ownership

The ten v2 files form the active self-contained contract, superseding v1. Use [backendschema-v2.md](backendschema-v2.md) for exact payloads and [trd-v2.md](trd-v2.md) for constants/algorithms; this document describes boundaries and dependencies.

```text
Public adapters / replay / custom injection
                 |
L1 Capture bytes -> evidence store + normalization + audit
                 |
      Immutable UnifiedSocialEvent
                 |
       async queue / job registry
                 |
L2 Text embeddings, narrative assignment, claim candidates, harm indicators
                 |
        +--------+---------+
        |                  |
L3 Image forensics   L4 Repeated co-posts, bot features, burst index
        |                  |
        |          L5 Interaction/sync graphs, Louvain, account roles
        |                  |
        +----------+-------+
                   |
        L6 Source/subject geography, coverage, baseline, mismatch
                   |
        L7 Available-component CTI and gated local alerts
                   |
 SQLite snapshots / audit + NumPy index + NetworkX views
                   |
 FastAPI jobs/reads + WebSocket -> Next.js investigation workbench
                   |
 Claim review and verified redacted investigative package
```

L3 may execute independently in a worker. L4 consumes L2 narrative/text-link evidence; it cannot infer same-narrative relations before L2. L5 depends on L4. L6 requires L4 campaign coordination for mismatch alerts. CTI recomputes versioned snapshots when optional media/geographic results arrive; unavailable results remain explicit.

The implemented local worker serializes queued CPU mutations through one executor; reads serve complete SQLite snapshots. Contextual reviews re-read the current revision under the mutation lock, and analytical publication merges any review arriving during calculation. Exact betweenness uses parity-tested sequential Rustworkx Brandes; NetworkX retains Louvain and graph construction. A retained method bundle and audit-anchored run manifest bind each new calculation to its inputs and implementation versions. See evaluation/README.md for measured limits and the unmet 800 ms graph target.

## 2. Seven layer boundaries

| Layer / module | Inputs | Outputs and responsibilities |
|---|---|---|
| 1 ingestion | source bytes, URLs, replay objects, uploaded media | raw and canonical evidence hashes; normalized immutable events; append-only audit |
| 2 nlp_engine | events, fixed embedder and registries | NarrativeCluster membership, harm report, candidate ClaimVerificationAssessment |
| 3 media_forensics | retained media bytes | ForensicMediaReport, pHash and heatmap artifacts; explicit unsupported states |
| 4 coordination | narrative events and text/content linkage | AccountSyncAssessment, BotAssessment, CoordinationAssessment with coverage |
| 5 graph_engine | interaction records and synchronization edges | typed GraphNode/GraphEdge, communities, observation-bounded roles |
| 6 geo_engine | source/subject locations, historical scope, coordination | GeoHexAnomaly with baseline_scope_id, coverage, counts, separate spike/mismatch indicators |
| 7 reporting / api | versioned reports, evidence store, analyst actions | CampaignThreatBreakdown, local alerts, jobs, verified dossiers and claim-review audit |

Engines depend on repository interfaces and schemas, not HTTP handlers. Keep exact raw payloads at the evidence boundary; downstream engines receive normalized models and authorized artifact bytes. Synthetic labels/annotations are evaluation data, never engine features.

## 3. Storage, immutability and lineage

SQLite stores events, memberships, analytical runs, jobs, references/reviews, baseline buckets and audit metadata. Content-addressed files retain raw payloads, immutable canonical serialization, exact media bytes and derived reports. Vector/graph indexes are rebuildable; no container service is mandatory.

Hash domains are distinct:
- raw_payload_sha256: retained original capture bytes;
- canonical_event_sha256: serialized initial event excluding its own hash;
- media sha256_hash: retained exact media bytes;
- artifact/audit hashes: derived artifacts and chained audit records.

Store source URL, collector/event key, capture manifest, capture format, pipeline version and parameter-set ID. Follow canonical-json-v1 and audit verification rules in the TRD. Enrichment never mutates initial evidence; later media retrieval is an appended collection record. Local hash chains are tamper-evidence relative to a retained manifest, not external attestation.

Repository adapters must support idempotent insert, append-only audit, immutable retrieval and integrity checks. A future Postgres/Qdrant/Neo4j adapter must preserve these contracts.

## 4. Event time, concurrency and origins

Partition analysis by DataOrigin and collector scope. SYNTHETIC_REPLAY, USER_INJECTED and PUBLIC_OSINT never silently mix. Similar narrative IDs in different partitions do not merge references or baselines.

Order analytical batches by event timestamp and stable ID; preserve actual collection_timestamp_utc independently. A replay controller advances event-time at a selectable speed while workers use the same services as live ingestion. Late-event handling, active windows and cooldowns follow the TRD.

Use asyncio.Queue for orchestration, CPU executors for expensive analysis, and persisted job states for progress. Store snapshot revision/generation so UI refreshes cannot combine stale graph and newer CTI. Reset serializes against queued mutations and invalidates the prior replay generation without deleting retained evidence.

Heavy mutation endpoints return 202 and jobs; upload returns an artifact ID; export is an explicit POST job. Use the complete endpoint table in the backend contract, rather than unversioned /api routes.

## 5. Scoring, uncertainty and interpretation

CTI base weights are sync .30, bot density .25, media .20, geo .15 and harm .10. Available components are renormalized, coverage and contribution breakdown are visible, and unavailable sync makes CTI unavailable. The score is an investigative prioritization index.

Numeric severity is LOW [0,40), MEDIUM [40,60), HIGH [60,75), CRITICAL [75,100]. An alert requires the TRD's separate coverage/sample/coordination gates; a high provisional score alone is insufficient. Local UI/WebSocket warnings can fire automatically; external dispatch is deferred.

Account roles include UNCLASSIFIED. Earliest observed seed is purely temporal, not necessarily influential or suspicious. Low observed indicators are not proof of authentic identity. Claim status changes require contextual human review; CTI and media scores never automatically determine truth.

## 6. Runtime, UI and failure handling

Backend: Python 3.11+, FastAPI/Pydantic v2, SQLite/NumPy/NetworkX/OpenCV/Pillow. Frontend: Next.js App Router/React/strict TypeScript, Tailwind, Canvas graph, Deck.gl/MapLibre map with offline outline fallback, and propagation chart.

Unavailable models use explicitly tagged text fallback or UNSUPPORTED media results. Missing geography/history shows null and coverage, not invented coordinates or baselines. Worker failures isolate affected reports and surface reasons. Reconnect uses bounded backoff plus REST/job polling.

Bind locally by default, enforce session-scoped access/CORS, public-only collection, safe uploads and privacy rules from rules-v2.md. External deployment, validated deepfake models and production evaluation are separate work.

## 7. Planned repository structure

```text
backend/app/
  main.py, config.py
  schemas/models.py
  ingestion/, nlp_engine/, media_forensics/, coordination/
  graph_engine/, geo_engine/, reporting/
  repositories/, evidence/, jobs/, api/
backend/tests/
frontend/src/
  app/, components/{graph,map,timeline,forensics,alerts,claims}/
  lib/, types/chakravyuh.ts
sample_data/
  raw/, media/, registries/, baselines/
docs v2/
```

Do not initialize these directories merely to mark a documentation task complete. Implementation status remains in tasks-v2.md and memory-v2.md.
