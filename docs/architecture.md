# System Architecture Document: Project Chakravyuh

**Project Name:** Chakravyuh  
**Architecture Pattern:** Event-Driven Multi-Layer Intelligence Pipeline  
**Version:** 1.0.0  

---

## 1. High-Level Architectural Overview (The 7 Rings of Chakravyuh)

Project Chakravyuh processes raw, noisy social media streams through seven specialized analytical rings. Each ring enriches the event payload and writes structured intelligence into polyglot storage engines that power the real-time Command Center.

```
+-----------------------------------------------------------------------------------+
|                        LAYER 1: OSINT INGESTION & REPLAY                          |
|   [X / Reddit / YouTube / Telegram Connectors] + [Synthetic Campaign Simulator]   |
+-----------------------------------------+-----------------------------------------+
                                          | (Raw JSON + Media Streams)
                                          v
                         +--------------------------------+
                         |  Apache Kafka / Redis Streams  |
                         |  (Canonical UnifiedSocialEvent)|
                         +----------------+---------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                 |                                 |
        v                                 v                                 v
+-----------------------+       +-----------------------+       +-----------------------+
| LAYER 2: NLP ENGINE   |       | LAYER 3: MULTIMEDIA   |       | LAYER 4: COORDINATION |
| - XLM-RoBERTa / Indic |       | - pHash / PDQ Dedup   |       | - Co-Posting Matrix   |
| - BERTopic Narratives |       | - ELA Image Splicing  |       | - Hawkes Burst Model  |
| - Toxicity / Incite   |       | - ViT / LipForensics  |       | - XGBoost Bot Scorer  |
+-----------+-----------+       +-----------+-----------+       +-----------+-----------+
            |                               |                               |
            +-------------------------------+-------------------------------+
                                            |
                     +----------------------+----------------------+
                     |                                             |
                     v                                             v
     +-------------------------------+             +-------------------------------+
     | LAYER 5: GRAPH TOPOLOGY       |             | LAYER 6: GEOSPATIAL ENGINE    |
     | - Louvain Cluster Detection   |             | - SpaCy / IndicNER Geo-Parser |
     | - PageRank & Centrality       |             | - Uber H3 Hex Grid Indexing   |
     | - Role Tagging (Patient Zero, |             | - Spatial Scan Spike Detector |
     |   Bridge, Bot Amplifier)      |             | - Astroturfing Mismatch Alert |
     +---------------+---------------+             +---------------+---------------+
                     |                                             |
                     +----------------------+----------------------+
                                            |
                                            v
+-----------------------------------------------------------------------------------+
|                     POLYGLOT PERSISTENCE & INDEXING LAYER                         |
|  [PostgreSQL: Metadata/Alerts]  [Qdrant: Vector Embeddings]  [Neo4j: Social Graph]|
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                 LAYER 7: COMMAND CENTER, EARLY WARNING & EXPORT                   |
|  - FastAPI REST + WebSockets        - Next.js Tactical Dashboard                  |
|  - Campaign Threat Index (CTI)      - D3/Cytoscape Network + Deck.gl H3 Map       |
|  - STIX 2.1 Threat Feed Exporter    - Court-Ready SHA-256 PDF Evidence Generator  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Detailed Layer Specifications

### Layer 1: OSINT Ingestion & Campaign Replay Engine
- **Components:** Asynchronous Python collectors (`httpx`, `Playwright`, official platform APIs) + deterministic **Campaign Replay Simulator** for testing and live demonstrations.
- **Responsibilities:**
  - Rate-limit aware harvesting of public posts, replies, reposts, user bios, and media URLs.
  - Immediate cryptographic hashing (`SHA-256`) of raw payload and media bytes to establish a forensic chain of custody.
  - Schema normalization into `UnifiedSocialEvent`.

### Layer 2: Multilingual NLP & Narrative Intelligence
- **Models & Tools:** `sentence-transformers` (`paraphrase-multilingual-mpnet-base-v2` / `IndicBERT`), `BERTopic`, `Qdrant` vector database.
- **Responsibilities:**
  - Encode post text into 768-dimensional vectors.
  - Query Qdrant using cosine similarity ($\ge 0.85$) over a 24-hour sliding window to link posts into an `EmergingNarrativeCluster`—catching copy-pasta mutations and translations.
  - Classify narrative intent: *Communal Incitement*, *Public Panic*, *Institutional Discrediting*, *Electoral Manipulation*, or *Benign*.

### Layer 3: Multimedia Verification & Deepfake Forensics
- **Models & Tools:** `ImageHash` (pHash/dHash), OpenCV Error Level Analysis (ELA), PyTorch `EfficientNet-B4` / Vision Transformer (`ViT`) deepfake detector, `exiftool` / `c2pa-python`.
- **Responsibilities:**
  - **Stage A (Fast Filter):** Compute 64-bit pHash; check Redis/Postgres for known manipulated media matches in $<5	ext{ms}$.
  - **Stage B (Deep Forensics):**
    - Generate ELA difference maps to highlight re-saved/spliced image regions.
    - Run deepfake classifier on extracted faces/frames and generate **Grad-CAM** visual attention heatmaps.
    - Inspect C2PA manifests and EXIF headers for AI tool signatures (e.g., Midjourney, Stable Diffusion, ElevenLabs) or stripped metadata.

### Layer 4: Behavioral & Temporal Coordination Engine
- **Algorithms:** Sliding-Window Co-Activity Bipartite Projection, Temporal Hawkes Process estimator, `XGBoost` Bot Classifier with `SHAP` explainability.
- **Responsibilities:**
  - Construct a temporal co-posting edge between accounts $u$ and $v$ whenever both post within $\Delta t \le 60	ext{s}$ within the same narrative cluster.
  - Update edge weight $w_{uv}$ exponentially based on repeated synchronization across multiple posts.
  - Score individual accounts on a `0–100` Bot Probability scale using 15+ behavioral features (inter-post time variance, circadian entropy, account age vs. volume, URL ratio).

### Layer 5: Social Network Graph & Propagation Topology
- **Tools:** `NetworkX` (fast in-memory subgraph analytics) + `Neo4j` (persistent graph storage).
- **Responsibilities:**
  - Run **Louvain Community Detection** on the weighted co-activity + interaction graph to isolate coordinated rings.
  - Reconstruct time-ordered diffusion cascades and assign functional roles:
    - `ORIGINATOR`: Earliest timestamp in cascade + high out-degree cascade reach.
    - `BOT_AMPLIFIER`: High temporal sync score ($\ge 0.75$) + high bot probability ($\ge 70$) + dense intra-cluster edges.
    - `BRIDGE_INFLUENCER`: High **Betweenness Centrality** connecting an isolated bot cluster to organic user communities.
    - `ORGANIC_USER`: Low sync score, natural response latency.

### Layer 6: Geospatial Anomaly & Astroturfing Engine
- **Tools:** `spaCy` / Indic NER, `h3-py` (Uber H3 Spatial Index at Resolution 5 & 7).
- **Responsibilities:**
  - Extract target locations (mentioned in post text) vs. source locations (account profile/GPS).
  - Map post velocity onto H3 hexagonal cells and calculate a Z-score spike metric:
    $$Z_{	ext{hex}} = rac{V_{	ext{current}} - \mu_{	ext{baseline}}}{\sigma_{	ext{baseline}}}$$
  - Compute the **Geospatial Mismatch Ratio (GMR)**: percentage of posts targeting a local H3 cell that originate from external/distant H3 cells. High GMR + High Coordination = **Astroturfing Alert**.

---

## 3. Campaign Threat Index (CTI) Formulation

Every active narrative cluster is continuously scored using the composite **Campaign Threat Index ($	ext{CTI} \in [0, 100]$)**:

$$	ext{CTI} = 0.30 \cdot S_{	ext{sync}} + 0.25 \cdot S_{	ext{bot\_density}} + 0.20 \cdot S_{	ext{media\_forensics}} + 0.15 \cdot S_{	ext{geo\_anomaly}} + 0.10 \cdot S_{	ext{harm\_severity}}$$

Where:
- $S_{	ext{sync}}$: Mean Cluster Synchronization Index ($0–100$).
- $S_{	ext{bot\_density}}$: Percentage of cluster volume generated by accounts with Bot Score $\ge 70$.
- $S_{	ext{media\_forensics}}$: Max deepfake/tampering confidence score attached to the narrative ($0–100$).
- $S_{	ext{geo\_anomaly}}$: Normalized H3 Z-score and Astroturfing Mismatch score ($0–100$).
- $S_{	ext{harm\_severity}}$: NLP toxicity/incitement classifier score ($0–100$).

**Alert Tiers:**
- `0–39 (LOW / ORGANIC)`: Normal public discourse.
- `40–69 (MEDIUM / WATCHLIST)`: Elevated amplification; queued for analyst review.
- `70–84 (HIGH / COORDINATED CAMPAIGN)`: Active bot/influence operation; triggers dashboard warning.
- `85–100 (CRITICAL / EARLY WARNING ALERT)`: High-velocity coordinated attack with deepfake/incitement payload; triggers immediate webhook & evidence snapshot.

---

## 4. Core Data Schemas

### 4.1 `UnifiedSocialEvent` (JSON / Pydantic)
```json
{
  "event_id": "evt_9f8a7d6c",
  "platform": "x_twitter",
  "timestamp_utc": "2026-10-18T10:14:22Z",
  "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "account": {
    "account_id": "acc_10492",
    "handle": "@Bot_Swarm_04",
    "created_at": "2026-09-12T00:00:00Z",
    "followers_count": 42,
    "following_count": 1850,
    "profile_location": "External Proxy"
  },
  "content": {
    "text": "URGENT: Visual proof of booth tampering in Sector 14! Share before deleted! #ElectionAlert",
    "language": "en",
    "hashtags": ["ElectionAlert"],
    "urls": ["https://t.co/xyz123"],
    "media_Attachments": [
      {
        "media_id": "med_8821",
        "media_type": "video",
        "phash": "f0e1d2c3b4a59687"
      }
    ]
  },
  "interaction": {
    "type": "repost",
    "parent_event_id": "evt_seed_001",
    "target_account_id": "acc_seed_01"
  },
  "geospatial": {
    "source_h3_index": "853c02affffffff",
    "target_mentioned_h3_index": "8560145ffffffff",
    "is_geo_mismatch": true
  }
}
```

---

## 5. Repository Directory Structure

```text
chakravyuh/
├── docs/
│   ├── PRD.md
│   ├── architecture.md
│   ├── rules.md
│   ├── design.md
│   ├── tasks.md
│   └── memory.md
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point & WebSocket manager
│   │   ├── config.py               # Environment & threshold configurations
│   │   ├── schemas/                # Pydantic v2 models (UnifiedSocialEvent, Alert, Dossier)
│   │   ├── ingestion/              # Layer 1: OSINT scrapers & Campaign Replay Simulator
│   │   ├── nlp_engine/             # Layer 2: Multilingual embeddings, BERTopic, toxicity
│   │   ├── media_forensics/        # Layer 3: pHash, ELA, Deepfake ViT, C2PA checker
│   │   ├── coordination/           # Layer 4: Co-posting matrices, Hawkes burst, Bot XGBoost
│   │   ├── graph_engine/           # Layer 5: Louvain clustering, centrality, role tagging
│   │   ├── geo_engine/             # Layer 6: NER geocoding, H3 indexing, astroturfing alerts
│   │   ├── reporting/              # Layer 7: CTI calculator, PDF Dossier & STIX 2.1 exporter
│   │   └── api/                    # REST & WebSocket route handlers
│   ├── tests/                      # Pytest unit & integration suites
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js App Router pages
│   │   ├── components/
│   │   │   ├── graph/              # D3 / Cytoscape force-directed network visualizer
│   │   │   ├── map/                # Deck.gl / MapLibre H3 hexagonal anomaly map
│   │   │   ├── forensics/          # Multimedia ELA/Grad-CAM split-screen inspector
│   │   │   ├── timeline/           # Narrative velocity & cascade propagation chart
│   │   │   └── alerts/             # Real-time CTI Early Warning drawer & Dossier modal
│   │   ├── lib/                    # API client, WebSocket hooks, color tokens
│   │   └── types/                  # TypeScript interfaces mirroring backend Pydantic schemas
│   └── package.json
└── docker-compose.yml              # Postgres, Redis, Qdrant, Neo4j, Backend, Frontend
```
