# Engineering Execution Backlog & Roadmap: Project Chakravyuh

**Project Name:** Chakravyuh  
**Tracking Convention:** Mark completed items with `[x]`, in-progress items with `[/]`, and pending items with `[ ]`. Update `memory.md` after completing each phase.

---

## Phase 0: Project Scaffolding & Core Contracts
- [ ] **T-0.1:** Initialize repository structure (`backend/`, `frontend/`, `docs/`, `sample_data/`).
- [ ] **T-0.2:** Create `backend/app/schemas/models.py` with strict Pydantic v2 models:
  - `UnifiedSocialEvent`, `AccountProfile`, `MediaAttachment`
  - `NarrativeCluster`, `GraphNode`, `GraphEdge`, `GeoHexAnomaly`
  - `ForensicMediaReport`, `CampaignThreatAssessment`, `EvidenceDossier`
- [ ] **T-0.3:** Set up `backend/app/config.py` with configurable detection thresholds (cosine similarity cutoff, temporal sync window seconds, CTI formula weights).
- [ ] **T-0.4:** Configure `docker-compose.yml` (or lightweight local SQLite/NetworkX/FAISS/Qdrant-in-memory fallback mode so the platform runs seamlessly on any machine without heavy infrastructure setup).

---

## Phase 1: OSINT Ingestion & Deterministic Campaign Simulator (Layer 1)
- [ ] **T-1.1:** Build `UnifiedEventNormalizer` with automatic `SHA-256` content hashing at ingestion time.
- [ ] **T-1.2:** Build the **Chakravyuh Multi-Scenario Campaign Simulator** (`backend/app/ingestion/simulator.py`) to generate realistic, time-stamped datasets for testing and live demos:
  - *Scenario A (Electoral Deepfake & Bot Swarm):* 1 Seed Originator + 25 synchronized Bot Amplifiers (co-posting within 12s) + 3 Bridge Influencers + 40 Organic Users + 1 manipulated video payload.
  - *Scenario B (Geospatial Communal Astroturfing):* Coordinated accounts located in Region X artificially spiking a panic narrative targeting District Y in English & Hinglish.
  - *Scenario C (Organic Baseline):* High-volume natural public conversation (sports/weather/traffic) to prove low false-positive rates.
- [ ] **T-1.3:** Implement live public OSINT connector adapters (Reddit/Telegram/X RSS/API hooks) that map into the same ingestion pipeline.

---

## Phase 2: Multilingual NLP & Narrative Clustering Engine (Layer 2)
- [ ] **T-2.1:** Implement text preprocessing & multilingual embedding pipeline (with fast local fallback for offline/low-latency execution).
- [ ] **T-2.2:** Build semantic similarity clustering engine to group paraphrased and code-mixed posts into `NarrativeCluster` objects.
- [ ] **T-2.3:** Implement Harm & Intent Classifier scoring posts across: *Communal Hatred*, *Public Panic*, *Institutional Discredit*, and *Electoral Manipulation*.

---

## Phase 3: Coordinated Behavior & Bot Detection Engine (Layer 4)
- [ ] **T-3.1:** Build the **Sliding-Window Co-Posting Matrix** builder (`backend/app/coordination/co_activity.py`) detecting accounts posting identical URLs, media hashes, or semantic claims within $\Delta t \le 60	ext{s}$.
- [ ] **T-3.2:** Implement the **Temporal Burst / Hawkes Process Analyzer** to calculate narrative velocity and separate organic rise-and-decay from synchronized swarm spikes.
- [ ] **T-3.3:** Implement the **Explainable Bot Probability Scorer** (`0–100`) outputting both the numeric score and the top human-readable `evidence_reasons` (account creation batching, circadian anomaly, sync latency, amplification ratio).

---

## Phase 4: Social Network Graph & Role Attribution Engine (Layer 5)
- [ ] **T-4.1:** Build the dynamic interaction & co-activity graph constructor using `NetworkX` (`backend/app/graph_engine/topology.py`).
- [ ] **T-4.2:** Integrate **Louvain Community Detection** to isolate dense coordination clusters and calculate the **Cluster Synchronization Index (CSI)**.
- [ ] **T-4.3:** Implement automated **Node Role Classifier** combining cascade timestamps, Out-Degree, and Betweenness Centrality to label:
  - `ORIGINATOR` ("Patient Zero")
  - `BOT_AMPLIFIER`
  - `BRIDGE_INFLUENCER`
  - `ORGANIC_USER`

---

## Phase 5: Multimedia Forensics & Geospatial Anomaly Engines (Layers 3 & 6)
- [ ] **T-5.1:** Implement Perceptual Hashing (`pHash`) deduplication and mutation tracker for images/memes.
- [ ] **T-5.2:** Implement **Error Level Analysis (ELA)** and Deepfake Forensic Scorer (`backend/app/media_forensics/verifier.py`) generating manipulation confidence scores, C2PA/EXIF metadata flags, and visual heatmap overlays.
- [ ] **T-5.3:** Build the **H3 Geospatial Anomaly Detector** (`backend/app/geo_engine/spatial.py`) calculating regional Z-score spikes and flagging **Source-to-Target Astroturfing Mismatches**.

---

## Phase 6: FastAPI Backend, CTI Alerting & Evidence Export (Layer 7 Backend)
- [ ] **T-6.1:** Implement the **Campaign Threat Index (CTI)** aggregator combining Layers 2–6 into a single `0–100` threat score and firing Early Warning Alerts.
- [ ] **T-6.2:** Create FastAPI REST endpoints (`/api/campaigns`, `/api/campaigns/{id}/graph`, `/api/campaigns/{id}/geo`, `/api/forensics/verify`, `/api/alerts`) and WebSocket live stream (`/ws/stream`).
- [ ] **T-6.3:** Build the **Court-Ready Evidence Dossier Exporter** generating a downloadable report + **STIX 2.1 Threat Intelligence JSON bundle** with SHA-256 chain-of-custody verification.

---

## Phase 7: Tactical Command Center Frontend (Layer 7 UI)
- [ ] **T-7.1:** Scaffold Next.js dark-mode application shell with top telemetry ribbon and campaign selector sidebar.
- [ ] **T-7.2:** Build the interactive **D3/Canvas Force-Directed Coordination Graph** with Sync Threshold slider, Role filter toggles, and Louvain cluster hulls.
- [ ] **T-7.3:** Build the **Geospatial Anomaly & Astroturfing Map** displaying regional spike heatmaps and source-to-target amplification arcs.
- [ ] **T-7.4:** Build the **Narrative Propagation Timeline** (Organic vs. Coordinated stacked velocity chart) and **Account Dossier Inspector Drawer**.
- [ ] **T-7.5:** Build the **Multimedia Forensics Workbench** modal with Original vs. ELA/Heatmap comparison view and C2PA provenance breakdown.

---

## Phase 8: Verification, Benchmarking & Demo Readiness
- [ ] **T-8.1:** Run end-to-end automated test suite verifying precision/recall on simulated campaigns and schema integrity across all API endpoints.
- [ ] **T-8.2:** Verify one-click demo scenario switching and Evidence Dossier export.
- [ ] **T-8.3:** Finalize documentation and update `memory.md` with release benchmarks.
