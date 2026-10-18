# UI/UX & Visualization Design Specification: Project Chakravyuh

**Project Name:** Chakravyuh  
**Design Theme:** Tactical Cyber-Intelligence Command Center ("Dark-Mode Glass & High-Contrast Telemetry")  
**Version:** 1.0.0  

---

## 1. Design Philosophy & UX Principles

Investigators monitoring live disinformation campaigns face high data velocity and cognitive overload. Project Chakravyuh's UI follows four core principles:
1. **Progressive Disclosure (Macro $ightarrow$ Meso $ightarrow$ Micro):**
   - **Macro:** Which narrative campaigns are spiking right now, and what is their Campaign Threat Index (CTI)?
   - **Meso:** How is the network structured (Originators, Bot Swarms, Bridge Influencers) and where is it spreading geographically?
   - **Micro:** Why was this specific account or video flagged (SHAP behavioral breakdown, ELA/Grad-CAM deepfake heatmap)?
2. **Zero-Ambiguity Semantic Color Coding:** Every color in the interface maps strictly to a threat level or network role—never use decorative rainbow palettes.
3. **Synchronized Cross-Filtering:** Clicking a narrative cluster in the left sidebar simultaneously filters the Force-Directed Network Graph, the H3 Geospatial Heatmap, the Propagation Timeline, and the Multimedia Forensics drawer.
4. **One-Click Forensic Export:** Every investigative view provides a direct action to snapshot the current state into a court-ready SHA-256 Evidence Dossier.

---

## 2. Color System & Semantic Tokens

### 2.1 Surface & Background Palette (Dark Mode Native)
| Token Name | Hex Code | Tailwind Equivalent | Usage |
| :--- | :--- | :--- | :--- |
| `bg-canvas` | `#070B14` | `bg-slate-950` | Main application background |
| `bg-panel` | `#0F172A` | `bg-slate-900` | Primary dashboard cards & sidebars |
| `bg-elevated` | `#1E293B` | `bg-slate-800` | Hover states, modals, inspector drawers |
| `border-subtle` | `#334155` | `border-slate-700` | Panel dividers and subtle grid lines |
| `accent-primary`| `#38BDF8` | `text-sky-400` | Active tabs, primary interactive controls |

### 2.2 Network Role & Threat Severity Palette
| Entity / Severity | Hex Code | Visual Treatment | Meaning |
| :--- | :--- | :--- | :--- |
| **Originator ("Patient Zero")** | `#EF4444` (Crimson) | Pulsing outer ring + star/diamond badge | Seed account that initiated the disinformation cascade |
| **Bot Amplifier (Swarm Node)** | `#F59E0B` (Amber) | Solid circle + dashed glowing sync edges | Automated or sockpuppet account acting in tight temporal lockstep |
| **Bridge Influencer** | `#A855F7` (Purple) | Dual-ring node + high radius | High-reach account bridging bot clusters into organic communities |
| **Organic User** | `#10B981` (Teal) | Muted translucent circle | Normal uncoordinated public discourse participant |
| **Deepfake / Tampered Media** | `#F43F5E` (Rose Red) | High-contrast warning badge | Verified synthetic or doctored multimedia payload |

---

## 3. Typography & Telemetry Formatting

- **Primary UI & Narrative Font:** `Inter` or `Plus Jakarta Sans` (Clean legibility for multilingual text, Hindi/Indic scripts, and analytical summaries).
- **Monospace Telemetry Font:** `JetBrains Mono` or `Fira Code` (Mandatory for all SHA-256 hashes, timestamps, H3 hex indices, Bot Scores, Sync Latencies, and CTI gauges using `tabular-nums`).

---

## 4. Command Center Layout & Wireframe Architecture

```
+--------------------------------------------------------------------------------------------------+
| [CHAKRAVYUH LOGO]   LIVE STREAM: ACTIVE   |  ACTIVE CAMPAIGNS: 4  |  CRITICAL ALERTS: 2  [EXPORT]|
+------------------------+------------------------------------------------+------------------------+
|                        |  [VIEW TABS: Network Graph | H3 Geo Map | Split] |                      |
|  EMERGING NARRATIVES   |                                                |  INVESTIGATOR DOSSIER  |
|  (Sorted by CTI Score) |                                                |  & FORENSICS DRAWER    |
|                        |         INTERACTIVE VISUAL WORKBENCH           |                        |
|  1. [CTI: 92 CRITICAL] |                                                |  Selected: @Seed_Matrix|
|     "Sector 14 Booth   |      (D3 Force-Directed Coordination Graph     |  Role: ORIGINATOR      |
|      Tampering Video"  |        with Louvain Cluster Hulls & Live       |  Bot Score: 88/100     |
|     - 142 Bot Nodes    |        Co-Posting Sync Threshold Slider)       |  Sync Latency: 4.2s    |
|     - Deepfake: 94%    |                                                |                        |
|                        |                      OR                        |  [SHAP Evidence Bars]  |
|  2. [CTI: 78 HIGH]     |                                                |  - Batch Creation: +32%|
|     "Water Supply      |      (Deck.gl H3 Hexagonal Spike Heatmap       |  - Co-Post <15s:  +41%|
|      Contamination"    |        with Astroturfing Source->Target Arcs)  |                        |
|     - Geo Mismatch!    |                                                |  MULTIMEDIA FORENSICS  |
|                        +------------------------------------------------+  [ELA / Grad-CAM View] |
|  3. [CTI: 24 ORGANIC]  |  NARRATIVE PROPAGATION & BURST TIMELINE        |  Deepfake Conf: 94.2%  |
|     "Metro Line Delay" |  [Area Chart: Amber = Coordinated | Teal = Org]|  [Download PDF Dossier]|
+------------------------+------------------------------------------------+------------------------+
```

---

## 5. Key Interactive Component Specifications

### 5.1 Chakravyuh Coordination Graph (`<CoordinationGraph />`)
- **Controls:**
  1. **Coordination Sync Threshold Slider (`0.20` to `0.95`):** Dynamically hides weak edges and highlights accounts co-posting within tight time windows.
  2. **Topology Lens Toggle:**
     - *Full Discourse Graph*
     - *Isolate Louvain Bot Rings* (draws convex hulls around synchronized clusters)
     - *Patient Zero Cascade Tree* (animates directional flow from Originator $ightarrow$ Amplifiers $ightarrow$ Bridges).
- **Micro-Interactions:** Hovering a node highlights its immediate ego-network and displays a tooltip with Handle, Role, Bot Score, and Time Offset from Seed.

### 5.2 Geospatial Astroturfing Map (`<GeospatialAnomalyMap />`)
- **Visual Encoding:**
  - **H3 Hexagons:** Color-scaled from dark slate (normal baseline) to glowing crimson (high Z-score narrative spike).
  - **Animated Arc Layer:** Curved glowing arcs connecting the **Source H3 Cell** (where the amplifying bot cluster is located) to the **Target H3 Cell** (the district/city mentioned in the narrative), immediately exposing external astroturfing.

### 5.3 Multimedia Forensics Workbench (`<MultimediaForensicsPanel />`)
- **Split-Screen Comparison Slider:** Allows the investigator to drag a vertical divider across a suspicious image/video frame to compare the **Original Media** against the **ELA Splicing Map** or **Grad-CAM Deepfake Attention Heatmap**.
- **Provenance Badge:** Displays C2PA cryptographic signature status (`Verified Camera Capture` vs. `Missing/Stripped EXIF` vs. `Synthetic AI Signature Detected`).
