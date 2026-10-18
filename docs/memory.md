# Project Memory & Context Log: Project Chakravyuh

**Project Name:** Chakravyuh — Social Media Coordinated Disinformation Detection System  
**Current Phase:** Phase 0 (Documentation & Architecture Initialized)  
**Last Updated:** October 18, 2026  

---

## 1. Core Project Identity & Mental Model
- **What we are building:** A near real-time OSINT, Graph Analytics, Multilingual NLP, Geospatial, and Multimedia Forensics platform that detects **coordinated disinformation campaigns** (bot swarms, astroturfing, deepfake amplification) and distinguishes them from organic public discourse.
- **Core Metaphor ("Chakravyuh"):** A 7-ring concentric intelligence architecture where each analytical layer traps a distinct signal of manipulation:
  1. **Ring 1:** OSINT Ingestion & SHA-256 Chain-of-Custody Normalization
  2. **Ring 2:** Multilingual NLP & Semantic Narrative Clustering
  3. **Ring 3:** Multimedia Verification & Deepfake Forensics (pHash, ELA, ViT, C2PA)
  4. **Ring 4:** Behavioral & Temporal Coordination Detection (Co-posting windows, Hawkes bursts, Bot XGBoost)
  5. **Ring 5:** Graph Topology & Role Attribution (Originator / Patient Zero, Bot Amplifier, Bridge Influencer, Organic User)
  6. **Ring 6:** Geospatial H3 Spike & Cross-Region Astroturfing Detection
  7. **Ring 7:** Command Center Dashboard, Campaign Threat Index (CTI) Early Warnings & Court-Ready Evidence Export

---

## 2. Architecture Decision Records (ADRs)

### ADR-001: Self-Contained Hybrid Execution Mode
- **Context:** Full distributed deployments require Kafka, Neo4j, Qdrant, and PostgreSQL, which can be heavy to spin up during rapid local development or live hackathon evaluations.
- **Decision:** Design repository interfaces using clean repository/adapter patterns so the backend runs out-of-the-box using an in-memory/local persistence layer (`NetworkX` + `NumPy/Cosine Vector Index` + `SQLite/JSON state`) while supporting drop-in `Neo4j` and `Qdrant` containers via `docker-compose.yml`.
- **Status:** Accepted.

### ADR-002: Deterministic Multi-Scenario Campaign Simulator
- **Context:** Live social media APIs have strict rate limits and unpredictable real-time attacks during a scheduled demonstration.
- **Decision:** Include a built-in **Campaign Replay & Simulation Engine** alongside live OSINT connectors. It streams realistic, time-stamped events (including coordinated bot rings, bridge influencers, Hinglish code-mixed posts, geospatial astroturfing, and manipulated media) through the exact same analytical pipeline.
- **Status:** Accepted.

### ADR-003: Mandatory Explainability ("No Black-Box Scores")
- **Context:** Law enforcement and government monitoring teams cannot act on opaque AI probabilities.
- **Decision:** Every analytical score (`bot_score`, `sync_score`, `deepfake_confidence`, `cti_score`) must attach structured `evidence_reasons` and visual proof artifacts (co-post delta timestamps, ELA heatmaps, SHA-256 hashes, STIX 2.1 bundles).
- **Status:** Accepted.

---

## 3. Canonical Thresholds & Constants Reference

| Parameter | Default Value | Description |
| :--- | :--- | :--- |
| `SEMANTIC_CLUSTER_SIMILARITY` | `0.85` | Cosine similarity cutoff to group posts into the same narrative cluster |
| `TEMPORAL_CO_POST_WINDOW_SEC` | `60` | Max time delta (seconds) between two posts to flag a synchronized co-posting edge |
| `BOT_PROBABILITY_HIGH_CUTOFF` | `70.0` | Account bot score (0–100) threshold to classify as high-risk automated/sockpuppet |
| `CLUSTER_SYNC_INDEX_THRESHOLD`| `0.65` | Default edge weight filter for isolating coordinated rings in the UI |
| `GEO_Z_SCORE_SPIKE_THRESHOLD` | `3.0` | Standard deviations above 30-day rolling baseline to flag a regional H3 spike |
| `ASTROTURFING_MISMATCH_RATIO` | `0.60` | Fraction of external-source volume targeting a local region required to trigger alert |
| `CTI_CRITICAL_ALERT_THRESHOLD`| `75.0` | Campaign Threat Index score (0–100) that triggers an immediate Early Warning Alert |

---

## 4. Session Progress & Changelog

- **[2026-10-18] Session 1 — Foundation Documentation Created:**
  - Created `PRD.md` defining functional requirements FR-1 through FR-6, personas, NFRs, and KPIs.
  - Created `architecture.md` detailing the 7-layer Chakravyuh pipeline, CTI mathematical formula, `UnifiedSocialEvent` schema, and repo structure.
  - Created `rules.md` establishing coding conventions, async rules, explainable forensics mandates, and ethical OSINT guardrails.
  - Created `design.md` specifying the dark-mode Tactical Command Center UI, semantic role colors, and interactive visualizations.
  - Created `tasks.md` breaking development into Phases 0 through 8.
  - **Next Step:** Begin **Phase 0 & Phase 1** in `tasks.md` (Initialize project directory structure, Pydantic schemas, and core analytical engines).
