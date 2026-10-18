# Application Flow & User Journey Specification: Project Chakravyuh

**Project Name:** Chakravyuh — Social Media Coordinated Disinformation Detection System  
**Document Version:** 1.0.0  
**Last Updated:** October 18, 2026  

---

## 1. End-to-End System Data Flow Overview

Project Chakravyuh operates through two tightly coupled loops:
1. **The Automated Intelligence Loop (Background Pipeline):** Continuously ingests events, clusters narratives, updates temporal co-posting graphs, evaluates multimedia forensics, and emits real-time Early Warning Alerts when the Campaign Threat Index ($	ext{CTI}$) crosses `75.0`.
2. **The Investigator Triage Loop (Interactive Command Center):** Guides an analyst from a high-level alert banner down to network role attribution ("Patient Zero"), geospatial astroturfing verification, deepfake inspection, and court-ready evidence export in under 3 minutes.

---

## 2. Automated Pipeline Data Flow (Layer 1 $ightarrow$ Layer 7)

```
[External Social Platforms / Replay Simulator]
                      │
                      ▼ (Raw Post + Media + Account Metadata)
        ┌───────────────────────────┐
        │ 1. Ingestion & Normalizer │ ──► Computes SHA-256 Hash & Canonical UnifiedSocialEvent
        └─────────────┬─────────────┘
                      │
        ┌─────────────┴───────────────────────────────────────────┐
        ▼                                                         ▼
┌───────────────────────────────┐                 ┌───────────────────────────────┐
│ 2. Multilingual NLP Engine    │                 │ 3. Multimedia Forensics       │
│ - Embeds Text (EN/HI/Hinglish)│                 │ - Computes 64-bit pHash       │
│ - Matches/Creates Narrative   │                 │ - Runs ELA Splicing Analysis  │
│   Cluster (Cosine >= 0.85)    │                 │ - Scores Deepfake & C2PA Meta │
└───────────────┬───────────────┘                 └───────────────┬───────────────┘
                │                                                 │
                └────────────────────────┬────────────────────────┘
                                         ▼
                        ┌─────────────────────────────────┐
                        │ 4. Behavioral Coordination      │
                        │ - Sliding Window Co-Post (<60s) │
                        │ - Hawkes Burstiness Estimation  │
                        │ - XGBoost + SHAP Bot Scoring    │
                        └────────────────┬────────────────┘
                                         │
                ┌────────────────────────┴────────────────────────┐
                ▼                                                 ▼
┌───────────────────────────────┐                 ┌───────────────────────────────┐
│ 5. Graph Topology Engine      │                 │ 6. Geospatial H3 Engine       │
│ - Louvain Cluster Isolation   │                 │ - Extracts Source vs Target   │
│ - Tags: ORIGINATOR, BRIDGE,   │                 │ - Computes H3 Hex Z-Score     │
│   BOT_AMPLIFIER, ORGANIC      │                 │ - Flags Astroturfing Mismatch │
└───────────────┬───────────────┘                 └───────────────┬───────────────┘
                │                                                 │
                └────────────────────────┬────────────────────────┘
                                         ▼
                        ┌─────────────────────────────────┐
                        │ 7. CTI Aggregator & Alert Engine│
                        │ - Calculates Composite CTI 0-100│
                        │ - Pushes WebSocket Alert if >=75│
                        └─────────────────────────────────┘
```

---

## 3. Investigator User Journeys (Step-by-Step)

### Flow A: Real-Time Early Warning Triage & Network Isolation
1. **Alert Trigger:** A synchronized swarm of 25 bot accounts begins amplifying a manipulated video claiming election booth tampering in Sector 14. Within seconds, the narrative's **Campaign Threat Index (CTI)** surges from `22` to `92 (CRITICAL)`.
2. **Banner Notification:** The top telemetry bar flashes a crimson badge (`CRITICAL ALERT: CTI 92 — Sector 14 Booth Tampering`). A live toast notification appears with a `[Investigate Campaign]` CTA.
3. **Macro Selection:** The analyst clicks the campaign card in the left sidebar (`Emerging Narratives`).
4. **Meso Graph Inspection:**
   - The center workbench loads the **D3 Force-Directed Coordination Graph**.
   - By default, nodes are colored by role: 1 Crimson **Originator** (`@Seed_TruthMatrix`), 25 Amber **Bot Amplifiers**, 2 Purple **Bridge Influencers**, and 35 Teal **Organic Users**.
   - The analyst drags the **Coordination Sync Threshold Slider** from `0.30` to `0.75` and toggles **"Isolate Coordinated Ring"**.
   - Uncoordinated organic nodes fade out; a glowing convex hull locks onto the 26-node coordinated ring, visually proving that the 25 bots posted within 12 seconds of `@Seed_TruthMatrix`.
5. **Micro Account Dossier:**
   - The analyst clicks the Crimson node `@Seed_TruthMatrix`.
   - The right-hand **Investigator Dossier Drawer** slides open, displaying:
     - **Assigned Role:** `ORIGINATOR ("Patient Zero")`
     - **Bot Probability Score:** `88 / 100`
     - **SHAP Evidence Breakdown:** `+41% Co-post synchronization (<12s)`, `+32% Account creation batch (Sept 12, 2026)`, `+15% External proxy location mismatch`.

---

### Flow B: Geospatial Astroturfing Verification
1. **Tab Switch:** While investigating Campaign #2 (*"Water Supply Contamination Rumor"*), the analyst notices a `GEO MISMATCH` warning badge and clicks the **[H3 Geospatial Map]** tab in the center workbench.
2. **Hexagonal Spike Inspection:**
   - The map renders Uber H3 hexagonal cells over the target district glowing Crimson ($Z = +6.4\sigma$ above the 30-day rolling baseline).
3. **Astroturfing Arc Analysis:**
   - Animated glowing purple/amber arcs curve across the map from distant Source H3 cells (where the amplifying accounts operate) into the Target H3 cell (the district named in the posts).
   - Hovering the Target Hexagon reveals: *"84% of posts claiming local water contamination originate from coordinated clusters outside the state (Geospatial Mismatch Ratio: 0.84)."*

---

### Flow C: Multimedia Deepfake & Splicing Forensics
1. **Media Flag Inspection:** In the right-hand Dossier Drawer (or the **[Multimedia Forensics]** modal), the analyst clicks on the flagged video/image attachment (`Deepfake Confidence: 94.2%`).
2. **Interactive Split-Screen Comparison:**
   - The forensics modal opens with the original media on the left and the **Error Level Analysis (ELA) / Grad-CAM Heatmap** overlay on the right.
   - Dragging the vertical comparison slider across the frame highlights bright high-contrast manipulation regions around the speaker's mouth and spliced ballot-box overlay.
3. **Provenance & Hash Verification:**
   - The bottom telemetry strip displays:
     - `pHash: f0e1d2c3b4a59687` (Matched 19 mutated reposts across 3 platforms).
     - `C2PA / EXIF Status: STRIPPED_METADATA + SYNTHETIC_AUDIO_SPECTRAL_ARTIFACT`.

---

### Flow D: Scenario Simulation & Live OSINT Replay Control
To support both live operations and deterministic demonstrations/training:
1. **Scenario Selector Dropdown (Top Header):** The analyst can switch between:
   - `Scenario 1: Electoral Deepfake & Bot Swarm (Critical CTI: 92)`
   - `Scenario 2: Communal Geospatial Astroturfing in Hinglish (High CTI: 81)`
   - `Scenario 3: Organic Public Discourse Baseline — Metro Delay (Low CTI: 18)`
   - `Live Stream Mode: Inject Custom Post / Media Payload`
2. **Live Injection Test:** Clicking **[+ Inject Test Event / Media]** allows the investigator (or hackathon evaluator) to paste custom text/hashtags or upload an image and watch it traverse all 7 layers in real time.

---

### Flow E: Court-Ready Evidence Dossier & STIX 2.1 Export
1. **Export Trigger:** Once the analyst confirms the campaign is orchestrated, they click **[Export Evidence Dossier]** in the top-right header.
2. **Privacy & Format Configuration:** A confirmation modal offers:
   - `[x] Anonymize Organic Bystander Handles (DPDP Act Compliance)`
   - `Export Format: [Court-Ready PDF Report] | [STIX 2.1 Threat Intel JSON]`
3. **Cryptographic Bundle Generation:** The backend compiles the campaign summary, Patient Zero attribution, top 10 synchronized bot accounts with SHAP explanations, geospatial mismatch metrics, media forensic heatmaps, and the full SHA-256 chain-of-custody manifest for immediate download.

---

## 4. UI State Machine & Error Recovery Flows

| UI State | Trigger | Visual Behavior & Recovery Action |
| :--- | :--- | :--- |
| **`LOADING_INITIAL`** | App mount / Scenario switch | Skeleton shimmer cards in sidebar + animated radar sweep on graph canvas |
| **`STREAM_CONNECTED`** | WebSocket `/ws/stream` open | Pulsing emerald indicator (`LIVE OSINT STREAM: ACTIVE`) |
| **`STREAM_RECONNECTING`**| WebSocket drop / timeout | Amber indicator (`RECONNECTING...`) + automatic fallback to 3s REST polling |
| **`CRITICAL_ALERT_ACTIVE`**| Any campaign $	ext{CTI} \ge 75$ | Crimson top border glow + sticky alert banner + optional audio chime |
| **`EMPTY_FILTER_RESULT`**| Sync slider set above max edge weight | Canvas overlay: *"No edges match Sync Threshold $\ge 0.95$. Lower threshold to inspect weaker links."* + `[Reset to 0.65]` button |
