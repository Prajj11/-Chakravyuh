# Product Requirements Document (PRD): Project Chakravyuh

**Project Name:** Chakravyuh — Social Media Coordinated Disinformation Detection System  
**Document Version:** 1.0.0  
**Last Updated:** October 2026  
**Status:** Approved for Development  

---

## 1. Executive Summary & Vision
**Project Chakravyuh** is an AI-driven Open-Source Intelligence (OSINT) and threat intelligence platform engineered to detect, analyze, and neutralize coordinated disinformation campaigns across social media in near real time. Inspired by the multi-layered *Chakravyuh* defensive formation, the platform processes public social data through seven concentric analytical rings—combining Multilingual NLP, Behavioral Coordination Analysis, Computer Vision Deepfake Forensics, Social Network Graph Analytics, and Geospatial Anomaly Detection.

The platform empowers law enforcement agencies (LEAs), government cyber-monitoring cells, election integrity units, and digital investigation teams with early warning alerts, interactive visual intelligence, and tamper-evident, court-ready evidence packages.

---

## 2. Problem Statement
Modern disinformation campaigns no longer rely on single viral fake posts. Instead, threat actors deploy orchestrated networks characterized by:
1. **Synchronized Swarm Amplification:** Automated botnets and click-farms posting identical or semantically paraphrased narratives within seconds to manipulate platform trending algorithms.
2. **Code-Mixed & Cross-Lingual Evasion:** Rapid mutation of false claims across English, regional languages, and code-mixed scripts (e.g., Hinglish, Tanglish) to bypass keyword-based moderation.
3. **Synthetic & Doctored Multimedia:** Weaponization of AI-generated deepfakes, voice clones, cheapfakes (speed/context alterations), and spliced memes to incite panic or communal disharmony.
4. **Geospatial Astroturfing:** External or non-local actor networks manufacturing artificial spikes in localized crisis narratives to instigate real-world unrest in targeted districts.

Existing social listening tools focus on vanity metrics (sentiment and volume) rather than **structural coordination, origin attribution, and forensic verification**.

---

## 3. Target Users & Personas
| Persona | Primary Role | Key Needs |
| :--- | :--- | :--- |
| **Law Enforcement & Cyber Cell Investigator** | Tracks unlawful incitement, communal triggers, and public order threats | Needs "Patient Zero" attribution, chain-of-custody evidence exports (SHA-256), and geospatial heatmaps of affected districts. |
| **National / State Threat Intelligence Analyst** | Monitors foreign and domestic influence operations & election interference | Needs macro-level Campaign Threat Index (CTI) early warnings, cross-platform narrative tracking, and STIX/TAXII threat feeds. |
| **Digital Forensics & Fact-Checking Specialist** | Verifies viral multimedia and debunks coordinated rumors | Needs deepfake confidence scores, pixel-level manipulation heatmaps (ELA/Grad-CAM), C2PA metadata inspection, and perceptual hash provenance. |

---

## 4. Functional Requirements

### FR-1: Multi-Platform OSINT & Content Analysis
- **FR-1.1:** Ingest publicly accessible posts, comments, reposts, profile metadata, and engagement metrics from supported platforms (X/Twitter, Telegram public channels, Reddit, YouTube, Instagram) and structured replay streams.
- **FR-1.2:** Normalize heterogeneous platform payloads into a canonical `UnifiedSocialEvent` schema.
- **FR-1.3:** Generate dense multilingual semantic embeddings (supporting English, Hindi, and major regional/code-mixed languages) to cluster semantically identical narratives even when keywords differ.
- **FR-1.4:** Score posts for toxicity, communal hate speech, panic inducement, and institutional credibility attacks.

### FR-2: Coordinated Account & Bot Network Detection
- **FR-2.1:** Detect temporal synchronization by identifying account pairs/groups sharing identical URLs, media hashes, or high-similarity text embeddings within configurable sliding time windows (e.g., $\le 60$ seconds).
- **FR-2.2:** Model narrative burstiness using Temporal Hawkes Processes to distinguish organic viral adoption curves from artificial, synchronized bot bursts.
- **FR-2.3:** Compute an explainable **Bot Probability Score (0–100)** per account using behavioral signals: circadian activity patterns, account creation batching, username entropy, amplification-to-creation ratio, and profile metadata anomalies.

### FR-3: Multimedia Verification & Deepfake Forensics
- **FR-3.1:** Compute perceptual hashes (**pHash / PDQ**) for all ingested images and video keyframes to track mutated or cropped variants of known disinformation media.
- **FR-3.2:** Perform **Error Level Analysis (ELA)** and Vision Transformer (**ViT**) forensic checks to detect image splicing, cloning, and diffusion/GAN frequency artifacts.
- **FR-3.3:** Analyze video and audio payloads for facial landmark jitter, phoneme-viseme (lip-sync) desynchronization, and synthetic voice spectral anomalies.
- **FR-3.4:** Extract and validate **EXIF** and **C2PA** cryptographic provenance metadata.
- **FR-3.5:** Output a unified **Multimedia Manipulation Confidence Score (0–100%)** accompanied by visual explainability artifacts (heatmap overlays and forensic breakdown tags).

### FR-4: Network Topology & Narrative Propagation Analysis
- **FR-4.1:** Construct dynamic, time-ordered directed interaction graphs (nodes = accounts, edges = retweets, replies, quotes, co-hashtags, temporal co-posts).
- **FR-4.2:** Execute community detection (**Louvain Modularity / Leiden**) to isolate dense, insular coordination clusters.
- **FR-4.3:** Automatically classify accounts within an active campaign into functional roles using graph centrality and cascade chronology:
  - **Originator ("Patient Zero"):** Earliest seed nodes initiating the cascade.
  - **Swarm Amplifier:** High-frequency, tightly synchronized bot/sockpuppet nodes inflating early volume.
  - **Bridge Influencer:** High-betweenness nodes transferring the narrative from fringe bot clusters into mainstream organic communities.
  - **Organic Participant:** Uncoordinated mainstream accounts engaging naturally.
- **FR-4.4:** Compute a **Cluster Synchronization Index (CSI)** to classify overall discourse as *Organic* vs. *Orchestrated*.

### FR-5: Geospatial Anomaly Detection
- **FR-5.1:** Resolve post geography using a three-tier fallback: (1) Explicit GPS/GeoJSON coordinates, (2) User profile location metadata, (3) NLP Named Entity Recognition (NER) extracting cities, districts, and landmarks mentioned in the text.
- **FR-5.2:** Aggregate narrative velocity into **Uber H3 hexagonal spatial grids** and detect statistically significant regional spikes against a rolling baseline.
- **FR-5.3:** Trigger **Geospatial Astroturfing Alerts** when a localized narrative targeting Region A is predominantly amplified by coordinated clusters physically located in Region B or external jurisdictions.

### FR-6: Investigation Dashboard, Early Warnings & Evidence Packaging
- **FR-6.1:** Calculate a real-time composite **Campaign Threat Index (CTI)** from 0 to 100 for every active narrative cluster.
- **FR-6.2:** Trigger automated early warning alerts (UI + Webhook) when CTI exceeds configurable thresholds (e.g., $	ext{CTI} \ge 75$).
- **FR-6.3:** Provide an interactive visual workbench featuring:
  - Force-directed account-linkage graph with role color-coding and sync-threshold filtering.
  - Narrative velocity timeline comparing organic vs. coordinated volume.
  - Geospatial H3 heatmap with astroturfing flow arcs.
  - Multimedia forensic inspection panel.
- **FR-6.4:** Export tamper-evident **Court-Ready Evidence Dossiers (PDF)** with SHA-256 content hashes and **STIX 2.1 JSON** bundles for threat intelligence sharing.

---

## 5. Non-Functional Requirements (NFRs)
1. **Performance & Latency:** Stream ingestion to vector/graph indexing latency must remain under 5 seconds for near real-time alerting. Dashboard graph queries up to 5,000 nodes must render within 1.5 seconds.
2. **Explainability & Legal Defensibility:** Zero "black-box" accusations. Every bot score, coordination link, and deepfake flag must expose top contributing features (SHAP values, exact co-post timestamps, or Grad-CAM heatmaps).
3. **Privacy & Ethical OSINT Compliance:** Strictly ingest publicly available data. Provide automated PII redaction toggles for non-suspect organic users in exported reports. Comply with India's Digital Personal Data Protection (DPDP) Act 2023 and IT Rules.
4. **Resilience & Modularity:** Micro-pipeline architecture where heavy ML inference (video forensics) scales independently without blocking text and graph ingestion.

---

## 6. Success Metrics & KPIs
- **Coordinated Cluster Detection F1-Score:** $\ge 0.88$ on benchmark & synthetic coordinated campaign datasets.
- **Deepfake / Tampered Media ROC-AUC:** $\ge 0.90$ across test sets of GAN, diffusion, and spliced media.
- **Mean Time to Detect (MTTD):** Identify an emerging coordinated campaign within 15 minutes of synchronized swarm activation.
- **Analyst Triage Efficiency:** Reduce manual investigation time from raw alert to exported evidence dossier by $>70\%$.
