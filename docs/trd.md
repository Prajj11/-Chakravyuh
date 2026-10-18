# Technical Requirements Document (TRD): Project Chakravyuh

**Project Name:** Chakravyuh — Social Media Coordinated Disinformation Detection System  
**Document Version:** 1.0.0  
**Last Updated:** October 18, 2026  
**Target Environment:** Hybrid Local-First (In-Memory / SQLite / NetworkX) & Cloud-Native (Docker / Kafka / Neo4j / Qdrant / PostgreSQL)

---

## 1. Purpose & Technical Scope
This Technical Requirements Document (TRD) translates the functional and architectural goals of **Project Chakravyuh** into concrete engineering specifications, model benchmarks, algorithmic formulations, API SLAs, hardware/runtime dependencies, and security controls. It serves as the authoritative technical contract for backend, ML/AI, graph, geospatial, and frontend engineers.

---

## 2. System Runtime & Dependency Stack

### 2.1 Backend & Intelligence Engine (`backend/`)
| Layer / Capability | Primary Package / Runtime | Version | Hybrid / Local Fallback |
| :--- | :--- | :--- | :--- |
| **Core Runtime & API** | Python + FastAPI + Uvicorn | Python `>=3.11`, FastAPI `>=0.115` | Native async event loop (`uvloop`) |
| **Data Validation** | Pydantic v2 + `pydantic-settings` | `>=2.9.0` | Strict runtime schema validation |
| **Stream Ingestion** | `aiokafka` / `redis.asyncio` | `>=0.11.0` | `asyncio.Queue` deterministic replay bus |
| **Multilingual NLP** | `sentence-transformers`, `bertopic` | `>=3.1.0` | TF-IDF + SVD / N-gram cosine embedder for zero-GPU mode |
| **Vector Indexing** | `qdrant-client` | `>=1.11.0` | `QdrantClient(":memory:")` or NumPy cosine matrix |
| **Multimedia Forensics** | `opencv-python`, `Pillow`, `imagehash`, `torch` | OpenCV `>=4.10`, PyTorch `>=2.4` | OpenCV ELA + perceptual hash (`pHash`/`dHash`) + EXIF/C2PA parser |
| **Coordination & Bot ML**| `scikit-learn`, `xgboost`, `shap`, `scipy` | XGBoost `>=2.1`, SHAP `>=0.46` | Heuristic + calibrated tree ensemble with exact feature attribution |
| **Graph Analytics** | `networkx`, `python-louvain` (`community`), `neo4j` | NetworkX `>=3.3` | In-memory `nx.MultiDiGraph` + Louvain modularity |
| **Geospatial Indexing** | `h3` (`h3-py`), `spacy` | `h3 >=3.7.7` | Gazetteer + H3 Resolution 5 & 7 hex indexer |
| **Forensic Reporting** | `reportlab` / `weasyprint`, `stix2` | `>=4.2.0` | Self-contained HTML/PDF generator + STIX 2.1 JSON serializer |

### 2.2 Frontend Tactical Command Center (`frontend/`)
| Capability | Package / Technology | Version | Technical Requirement |
| :--- | :--- | :--- | :--- |
| **Application Framework** | Next.js (App Router) + React + TypeScript | Next `14.2+`, TS `5.5+` | `strict: true`, zero implicit `any` |
| **Styling & UI Primitives**| Tailwind CSS + Lucide Icons + Radix UI | Tailwind `3.4+` | Dark-mode native (`#070B14` canvas) |
| **Network Graph Engine** | `d3-force` / `react-force-graph-2d` / `cytoscape` | `d3 >=7.9` | HTML5 Canvas/WebGL rendering for $\ge 500$ nodes at 60 FPS |
| **Geospatial Engine** | `deck.gl` (`H3HexagonLayer`, `ArcLayer`) + `maplibre-gl` | `deck.gl >=9.0` | Interactive H3 hex rendering + source-to-target astroturfing arcs |
| **Telemetry & Charts** | `recharts` / `visx` | `>=2.12` | Stacked area velocity charts (Coordinated vs. Organic) |
| **Real-Time Transport** | Native `WebSocket` + `SWR` / `TanStack Query` | Native Web API | Auto-reconnect with exponential backoff (`1s`, `2s`, `4s`, `8s`) |

---

## 3. Algorithmic & Mathematical Specifications by Layer

### 3.1 Layer 1: Cryptographic Chain-of-Custody Normalization
Every ingested post must generate a deterministic content signature prior to database persistence:
$$	ext{Hash}_{	ext{event}} = 	ext{SHA256}\left(	ext{platform} \parallel 	ext{account\_id} \parallel 	ext{timestamp\_utc} \parallel 	ext{normalized\_text} \parallel 	ext{media\_phash}ight)$$
- **Requirement:** Any mutation to post text or timestamps after ingestion invalidates the signature and flags a tamper warning during Evidence Dossier export.

### 3.2 Layer 2: Multilingual Narrative Clustering & Harm Scoring
1. **Embedding & Clustering:**
   - Input text $T_i$ (English, Hindi, or code-mixed Hinglish/Tanglish) is mapped to a unit-normalized embedding vector $\mathbf{e}_i \in \mathbb{R}^{d}$.
   - Pairwise similarity with existing active narrative centroids $\mathbf{c}_k$ is computed via cosine similarity:
     $$	ext{sim}(\mathbf{e}_i, \mathbf{c}_k) = rac{\mathbf{e}_i \cdot \mathbf{c}_k}{\|\mathbf{e}_i\| \|\mathbf{c}_k\|}$$
   - If $\max_k 	ext{sim}(\mathbf{e}_i, \mathbf{c}_k) \ge 	au_{	ext{sim}}$ (where $	au_{	ext{sim}} = 0.85$), assign event $i$ to cluster $k$ and update centroid $\mathbf{c}_k$ via exponential moving average. Otherwise, initialize a new `NarrativeCluster`.
2. **Harm & Intent Classification:**
   - Multi-label classification across 4 threat vectors: `COMMUNAL_INCITEMENT`, `PUBLIC_PANIC`, `ELECTORAL_MANIPULATION`, `INSTITUTIONAL_DISCREDIT`.
   - Output calibrated probability $H_i \in [0, 100]$.

### 3.3 Layer 3: Multimedia Forensics & Deepfake Verification
1. **Perceptual Hashing (Stage A):**
   - Compute 64-bit Discrete Cosine Transform (DCT) perceptual hash (`pHash`).
   - Hamming distance $D_H(h_1, h_2) \le 10$ bits flags a mutated/cropped derivative of a known disinformation artifact.
2. **Error Level Analysis — ELA (Stage B1):**
   - Re-compress input image $I_{	ext{orig}}$ at JPEG quality $Q = 90\%$ to obtain $I_{90}$.
   - Compute pixel-wise absolute difference amplified by scale factor $lpha = 15$:
     $$I_{	ext{ELA}}(x, y) = \min\left(255, lpha \cdot |I_{	ext{orig}}(x, y) - I_{90}(x, y)|ight)$$
   - High variance in localized bounding boxes indicates digital splicing or text/logo overlay tampering.
3. **Deepfake & Synthetic Media Scoring (Stage B2):**
   - Combine visual frequency/artifact score $S_{	ext{visual}}$, facial/lip-sync temporal consistency score $S_{	ext{temporal}}$, and EXIF/C2PA provenance penalty $S_{	ext{meta}}$:
     $$S_{	ext{media\_forensics}} = 0.50 \cdot S_{	ext{visual}} + 0.35 \cdot S_{	ext{temporal}} + 0.15 \cdot S_{	ext{meta}}$$

### 3.4 Layer 4: Temporal Synchronization & Bot Probability Scoring
1. **Sliding-Window Co-Activity Matrix:**
   - Given events $e_a = (u, t_a, k)$ and $e_b = (v, t_b, k)$ in the same narrative cluster $k$ where $u 
eq v$:
   - If $0 < |t_a - t_b| \le \Delta t_{	ext{max}}$ ($\Delta t_{	ext{max}} = 60	ext{s}$), increment temporal coupling weight:
     $$w_{uv}^{(n)} = w_{uv}^{(n-1)} + \exp\left(-rac{|t_a - t_b|}{	au_{	ext{decay}}}ight), \quad 	au_{	ext{decay}} = 20	ext{s}$$
   - Normalize into a pair synchronization score $S_{	ext{sync}}(u, v) \in [0.0, 1.0]$.
2. **Hawkes Process Burstiness Index:**
   - Model cluster event arrival intensity $\lambda(t)$ as a self-exciting point process:
     $$\lambda(t) = \mu + \sum_{t_i < t} lpha \exp(-eta (t - t_i))$$
   - A branching ratio $\hat{\eta} = rac{lpha}{eta} > 0.80$ combined with low unique-author diversity within the first 5 minutes triggers a `SYNCHRONIZED_SWARM_BURST` flag.
3. **Explainable Bot Probability Score ($B_u \in [0, 100]$):**
   - Features evaluated per account $u$:
     - `f1_sync_latency_mean`: Average time delta (seconds) from cluster seed post.
     - `f2_creation_batch_density`: Number of co-active accounts created within the same 48-hour window.
     - `f3_circadian_entropy`: Shannon entropy of posting activity across 24 hourly bins.
     - `f4_amplification_ratio`: Ratio of reposts/identical copy-posts to original replies.
     - `f5_handle_digit_entropy`: Character-level randomness and trailing numeric suffix pattern.
   - Must output top 3 feature attributions (`feature_contributions`) and human-readable `evidence_reasons`.

### 3.5 Layer 5: Graph Topology & Role Classification Rules
Given cluster interaction & synchronization graph $G = (V, E, W)$:
1. **Community Detection:** Execute Louvain modularity maximization (`resolution=1.0`) to partition $V$ into communities $\{C_1, C_2, \dots, C_m\}$.
2. **Deterministic Role Assignment Heuristics:**
   - **`ORIGINATOR` ("Patient Zero"):**
     $$	ext{argmin}_{u \in C_{	ext{coord}}} (t_{	ext{first}}(u)) \quad 	ext{subject to} \quad 	ext{OutDegree}(u) \ge P_{80}(	ext{OutDegree})$$
   - **`BOT_AMPLIFIER` (Swarm Node):**
     $$B_u \ge 70.0 \quad \land \quad 	ext{MeanSync}(u) \ge 0.65$$
   - **`BRIDGE_INFLUENCER`:**
     $$	ext{BetweennessCentrality}(u) \ge P_{85}(	ext{Betweenness}) \quad \land \quad 	ext{CrossCommunityEdges}(u, C_{	ext{coord}} ightarrow C_{	ext{organic}}) \ge 2$$
   - **`ORGANIC_USER`:** All remaining nodes with $B_u < 50.0$ and $	ext{MeanSync}(u) < 0.45$.

### 3.6 Layer 6: H3 Geospatial Spike & Astroturfing Detection
1. **Regional Spike Z-Score:**
   - For each H3 cell $h$ (Resolution 5 for state/regional view, Resolution 7 for city/district view):
     $$Z_h = rac{V_{h, 	ext{1hr}} - \mu_{h, 	ext{30d}}}{\max(\sigma_{h, 	ext{30d}}, 1.0)}$$
   - Flag anomaly if $Z_h \ge 3.0$.
2. **Geospatial Mismatch Ratio (GMR):**
   - For a narrative targeting H3 cell $h_{	ext{target}}$ (extracted via NER from post text):
     $$	ext{GMR}(h_{	ext{target}}) = rac{\sum_{e \in E(h_{	ext{target}})} \mathbb{I}(	ext{dist}(h_{	ext{source}}(e), h_{	ext{target}}) > 2 	ext{ hex rings})}{|E(h_{	ext{target}})|}$$
   - If $	ext{GMR}(h_{	ext{target}}) \ge 0.60$ and cluster coordination $S_{	ext{sync}} \ge 65$, raise an `ASTROTURFING_MISMATCH_ALERT`.

---

## 4. Performance, Scalability & Reliability SLAs

| Metric | Target SLA | Verification Method |
| :--- | :--- | :--- |
| **Event Ingestion & Normalization Throughput** | $\ge 500 	ext{ events/sec}$ per worker | Async load test in `pytest` benchmark |
| **REST API P95 Response Latency** | $< 200 	ext{ ms}$ | FastAPI middleware timing header (`X-Process-Time-Ms`) |
| **Graph Re-computation Latency (up to 1,000 nodes)** | $< 800 	ext{ ms}$ | NetworkX Louvain + Centrality benchmark |
| **WebSocket Alert Push Latency** | $< 1.5 	ext{ seconds}$ from threshold breach | End-to-end simulator-to-UI timestamp delta |
| **Evidence Dossier Generation Time** | $< 2.0 	ext{ seconds}$ | PDF + STIX 2.1 export endpoint test |

---

## 5. Security, Privacy & Regulatory Compliance

1. **Cryptographic Integrity:** All exported Evidence Dossiers include a manifest of SHA-256 hashes for every post, account snapshot, and media payload, signed with a server verification timestamp.
2. **Organic Bystander Anonymization:** When ` redact_organic_pii=True` (default in exported reports), handles of accounts classified as `ORGANIC_USER` are masked as `@Organic_User_<first_6_chars_of_sha256>`.
3. **API Rate Limiting & CORS:** Restrict CORS origins in production; enforce token-bucket rate limiting on `/api/forensics/verify` media upload routes (max file size `25 MB`, allowed MIME types: `image/jpeg`, `image/png`, `image/webp`, `video/mp4`).
