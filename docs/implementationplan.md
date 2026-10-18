# Step-by-Step Implementation Plan: Project Chakravyuh

**Project Name:** Chakravyuh — Social Media Coordinated Disinformation Detection System  
**Document Version:** 1.0.0  
**Last Updated:** October 18, 2026  
**Execution Strategy:** Bottom-Up Vertical Slices (Schemas $ightarrow$ Simulator $ightarrow$ 7 Analytical Rings $ightarrow$ FastAPI $ightarrow$ Command Center UI)

---

## 1. Implementation Roadmap & Sprint Breakdown

To ensure the system is testable at every milestone and avoids integration bottlenecks, development is organized into **6 Execution Sprints** mapping directly to `tasks.md`.

```
Sprint 1: Core Contracts & Deterministic Campaign Simulator (Layers 1 & Schemas)
   │
   ▼
Sprint 2: Multilingual NLP & Temporal Coordination Engine (Layers 2 & 4)
   │
   ▼
Sprint 3: Social Network Graph Topology & Role Classifier (Layer 5)
   │
   ▼
Sprint 4: Multimedia Forensics & H3 Geospatial Astroturfing (Layers 3 & 6)
   │
   ▼
Sprint 5: CTI Aggregator, FastAPI Endpoints & STIX/PDF Exporter (Layer 7 Backend)
   │
   ▼
Sprint 6: Tactical Command Center UI & End-to-End Verification (Layer 7 Frontend)
```

---

## 2. Module-by-Module Implementation Blueprint

### Sprint 1: Foundation, Schemas & Multi-Scenario Simulator
**Goal:** Establish 100% typed data models and a rich, deterministic data generator that produces realistic coordinated attacks and organic traffic.

1. **`backend/app/config.py`**:
   - Centralize all thresholds from `memory.md` (`SEMANTIC_CLUSTER_SIMILARITY = 0.85`, `TEMPORAL_CO_POST_WINDOW_SEC = 60`, `BOT_PROBABILITY_HIGH_CUTOFF = 70.0`, `CTI_CRITICAL_ALERT_THRESHOLD = 75.0`).
2. **`backend/app/schemas/models.py`**:
   - Implement all Pydantic v2 models defined in `backendschema.md`.
3. **`backend/app/ingestion/normalizer.py`**:
   - Implement `UnifiedEventNormalizer.normalize(raw_payload)` which strips tracking parameters from URLs, canonicalizes timestamps to UTC, and computes the immutable `sha256_hash`.
4. **`backend/app/ingestion/simulator.py`**:
   - Build `ChakravyuhScenarioGenerator` with 3 rich, pre-seeded campaigns:
     - **Campaign 1 (`cmp_electoral_01` — Critical Coordinated Attack, CTI ~92):**
       - *Narrative:*Manipulated video alleging ballot/booth tampering in Sector 14 (`#Sector14Alert`, English + Hinglish mutations).
       - *Topology:* 1 Originator (`@Seed_TruthMatrix`), 18 synchronized Bot Amplifiers posting within `4s–18s`, 2 Bridge Influencers (`@Viral_Voice_IN`, `@Breaking_Pulse`), and 15 Organic Users.
       - *Media:* Attached video with `94.2%` deepfake confidence, lip-sync drift, and stripped EXIF.
     - **Campaign 2 (`cmp_geo_astroturf_02` — High Geospatial Astroturfing, CTI ~81):**
       - *Narrative:* Coordinated panic posts claiming water supply contamination in District North (`"Paani mein zahar milaya gaya hai"` / `"Emergency in District North water grid"`).
       - *Topology:* 1 Originator + 14 coordinated amplifiers physically geolocated in external proxy H3 cells, targeting District North's H3 hex ($Z = +6.4\sigma$, $	ext{GMR} = 0.84$).
     - **Campaign 3 (`cmp_organic_03` — Benign Organic Discourse, CTI ~18):**
       - *Narrative:* Natural commuter discussion about rain delays on the Metro Blue Line.
       - *Topology:* 25 uncoordinated organic users with natural reaction intervals (`180s–3600s`), zero bot batching, and authentic camera EXIF photos.

---

### Sprint 2: Multilingual NLP (Layer 2) & Behavioral Coordination (Layer 4)
**Goal:** Group cross-lingual/paraphrased claims into narrative clusters and detect synchronized bot swarms.

1. **`backend/app/nlp_engine/narrative_clustering.py`**:
   - Implement `MultilingualNarrativeEngine`:
     - Uses `sentence-transformers` if GPU/weights are cached, with an instant deterministic character/word N-gram + cross-lingual synonym embedding fallback so the app runs offline in $<10	ext{ms}$.
     - Computes cosine similarity against active centroids and scores `HarmCategory` using curated multilingual threat lexicons + intent weights.
2. **`backend/app/coordination/co_activity.py`**:
   - Implement `TemporalCoordinationAnalyzer`:
     - Sorts cluster events chronologically.
     - Builds pairwise temporal coupling weights $w_{uv} = \sum \exp(-\Delta t / 20.0)$ for posts occurring within `60s`.
     - Computes the Hawkes process burstiness score to distinguish swarm spikes from organic growth.
3. **`backend/app/coordination/bot_scorer.py`**:
   - Implement `ExplainableBotScorer`:
     - Evaluates the 5 core behavioral features per account (`sync_latency`, `creation_batch_density`, `circadian_entropy`, `amplification_ratio`, `handle_entropy`).
     - Returns `bot_probability_score` (`0–100`), `feature_contributions` dictionary, and human-readable `evidence_reasons`.

---

### Sprint 3: Social Network Graph & Role Attribution (Layer 5)
**Goal:** Construct the network topology, isolate Louvain bot clusters, and tag Originators and Bridges.

1. **`backend/app/graph_engine/topology.py`**:
   - Implement `ChakravyuhGraphEngine`:
     - Builds a `networkx.DiGraph` combining direct interactions (`repost`, `reply`, `quote`) and temporal synchronization edges (`CO_POST_SYNC`).
     - Runs Louvain modularity (`nx.community.louvain_communities`) to assign `community_id`.
     - Computes `nx.betweenness_centrality` and out-degree cascades.
     - Applies the deterministic Role Attribution rules from `trd.md` to tag each node as `ORIGINATOR`, `BOT_AMPLIFIER`, `BRIDGE_INFLUENCER`, or `ORGANIC_USER`.

---

### Sprint 4: Multimedia Forensics (Layer 3) & Geospatial Engine (Layer 6)
**Goal:** Verify manipulated images/videos and detect cross-region astroturfing spikes.

1. **`backend/app/media_forensics/verifier.py`**:
   - Implement `MultimediaForensicsVerifier`:
     - Computes 64-bit `pHash` and checks hamming distance against known campaign artifacts.
     - Runs OpenCV/Pillow **Error Level Analysis (ELA)** on image buffers to detect high-contrast spliced regions and outputs normalized bounding-box heatmap coordinates for the UI slider.
     - Evaluates C2PA/EXIF metadata headers and combines scores into a `ForensicMediaReport`.
2. **`backend/app/geo_engine/spatial.py`**:
   - Implement `GeospatialAnomalyDetector`:
     - Maps regional coordinates to H3 Resolution 5/7 indices.
     - Computes hourly velocity Z-scores and the **Geospatial Mismatch Ratio (GMR)**, generating source-to-target arc coordinates for Deck.gl / SVG map rendering.

---

### Sprint 5: CTI Aggregator, FastAPI Server & Evidence Dossier Exporter (Layer 7 Backend)
**Goal:** Expose all intelligence via clean REST/WebSocket APIs and generate court-ready reports.

1. **`backend/app/reporting/cti_calculator.py`**:
   - Implements the exact weighted Campaign Threat Index formula:
     $$	ext{CTI} = 0.30 S_{	ext{sync}} + 0.25 S_{	ext{bot}} + 0.20 S_{	ext{media}} + 0.15 S_{	ext{geo}} + 0.10 S_{	ext{harm}}$$
2. **`backend/app/reporting/dossier_exporter.py`**:
   - Generates a structured **STIX 2.1 Threat Intelligence Bundle** (`campaign`, `threat-actor`, `indicator`, `observed-data`) and an HTML/PDF **Court-Ready Evidence Dossier** complete with SHA-256 chain-of-custody tables and optional organic PII redaction.
3. **`backend/app/main.py`**:
   - FastAPI application with CORS middleware, startup initialization of the 3 simulated campaigns, REST endpoints matching `backendschema.md`, and `/ws/stream` WebSocket broadcaster.

---

### Sprint 6: Tactical Command Center Frontend (Layer 7 UI)
**Goal:** Build the dark-mode cyber-intelligence workbench defined in `design.md`.

1. **Top Telemetry Header (`<CommandHeader />`):**
   - Displays live stream status, active campaign counter, critical alert banner, Scenario Switcher dropdown, `[+ Inject Event]` button, and `[Export Evidence Dossier]` CTA.
2. **Left Sidebar (`<CampaignFeedSidebar />`):**
   - Lists emerging narrative campaigns sorted by CTI badge (`CRITICAL 92`, `HIGH 81`, `LOW 18`) with mini sparklines and threat tags (`DEEPFAKE`, `BOT SWARM`, `GEO ASTROTURF`).
3. **Center Interactive Workbench (`<IntelligenceWorkbench />`):**
   - **Tab 1: Force-Directed Coordination Graph:** Interactive HTML5 Canvas / SVG network graph with **Coordination Sync Threshold Slider (`0.20–0.95`)**, **Role Filter Pills**, convex cluster hulls, and directional cascade pulse animations.
   - **Tab 2: H3 Geospatial Astroturfing Map:** Interactive regional H3 hexagonal grid with Z-score spike coloring and glowing curved **Source $ightarrow$ Target Astroturfing Arcs**.
   - **Tab 3: Multimedia Forensics Inspector:** Interactive split-screen **Original vs. ELA / Deepfake Heatmap Slider**, pHash duplicate counter, and C2PA provenance breakdown.
   - **Bottom Panel: Narrative Propagation Timeline:** Stacked area chart comparing **Coordinated Bot Volume (Amber)** vs. **Organic Discourse Volume (Teal)** over time with Hawkes burst markers.
4. **Right Inspector Drawer (`<AccountDossierDrawer />`):**
   - Displays selected node role badge, Bot Probability gauge, Sync Latency (`s`), Account Creation Batch alert, and horizontal **SHAP Feature Contribution Bars**.

---

## 3. Verification & Automated Testing Matrix

| Test Suite | File Location | What It Validates |
| :--- | :--- | :--- |
| **Unit: Cryptographic Normalizer** | `backend/tests/test_ingestion.py` | Verifies deterministic SHA-256 hashing and schema normalization. |
| **Unit: Coordination & Bot Scorer**| `backend/tests/test_coordination.py`| Verifies accounts co-posting within `<15s` receive `sync_score > 0.85` and non-empty `evidence_reasons`. |
| **Unit: Graph Role Attribution** | `backend/tests/test_graph_roles.py` | Verifies `@Seed_TruthMatrix` is tagged `ORIGINATOR` and bridge nodes are tagged `BRIDGE_INFLUENCER`. |
| **Unit: Geospatial Astroturfing** | `backend/tests/test_geo_engine.py` | Verifies external-source amplification triggers `is_astroturfing_alert = True` when $	ext{GMR} \ge 0.60$. |
| **Integration: End-to-End API** | `backend/tests/test_api_e2e.py` | Tests `/api/v1/campaigns`, `/api/v1/events/inject`, and STIX 2.1 dossier export with PII redaction. |

---

## 4. Quick-Start Execution Commands

```bash
# 1. Start Backend Intelligence Server (Port 8000)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. Run Automated Pytest Verification Suite
pytest tests/ -v

# 3. Start Next.js Tactical Command Center (Port 3000)
cd ../frontend
npm install
npm run dev
```
