# Engineering, AI Assistant & Governance Rules: Project Chakravyuh

**Project Name:** Chakravyuh  
**Scope:** Mandatory development standards for human engineers and AI coding agents (Cursor, Windsurf, Claude Code, GitHub Copilot).  

---

## 1. Core Architectural Laws

1. **Strict Layer Decoupling:**
   - Each of the 7 Chakravyuh layers (`ingestion`, `nlp_engine`, `media_forensics`, `coordination`, `graph_engine`, `geo_engine`, `reporting`) must remain modular with clearly defined input/output Pydantic contracts.
   - Never import frontend or API route logic into core ML/Graph engines.
2. **Canonical Schema Enforcement:**
   - No raw platform-specific JSON (e.g., raw X/Twitter or Telegram payloads) is allowed past Layer 1. Every event must be validated and normalized into `UnifiedSocialEvent` before processing.
3. **Non-Blocking Asynchronous Execution:**
   - FastAPI HTTP endpoints must respond in $<200	ext{ms}$ for standard reads.
   - Compute-heavy operations (Deepfake frame analysis, Transformer batch embeddings, full-graph Louvain recalculations) must run asynchronously in background tasks or worker queues (`asyncio` / Redis tasks) and push updates via WebSockets.

---

## 2. Explainable AI & Forensic Integrity Rules ("Zero Black-Box Rule")

Because Project Chakravyuh supports law enforcement and institutional investigations, **unexplained AI scores are strictly forbidden**:
1. **Mandatory Evidence Reasons:**
   - Every `bot_probability_score`, `coordination_sync_score`, `deepfake_confidence`, and `campaign_threat_index` object returned by the backend MUST include a human-readable `evidence_reasons: list[str]` field and a structured `feature_contributions: dict[str, float]` breakdown.
   - *Bad:* `{"bot_score": 92}`
   - *Good:* `{"bot_score": 92, "evidence_reasons": ["Co-posted 14 times within 8s of @Seed_Account", "Account created in batch of 45 accounts on 2026-09-12", "24/7 posting without circadian rest window"]}`
2. **Chain-of-Custody Hashing:**
   - Upon ingestion, compute and store an immutable `sha256_hash` of the canonical post content and any media payload. Never mutate raw evidence fields after ingestion.
3. **Distinguish Suspicion from Fact:**
   - UI labels and exported reports must use precise forensic terminology: *"Coordinated Amplification Probable (Confidence: 94%)"*, *"Synthetic Media Indicators Detected"*, or *"High Temporal Synchronization"* rather than unverified legal conclusions.

---

## 3. Coding Standards & Tech Stack Conventions

### 3.1 Python Backend & ML (`backend/`)
- **Version:** Python 3.11+
- **Typing:** 100% type annotations required on all function signatures (`def compute_cti(cluster: NarrativeCluster) -> ThreatAssessment:`). Use **Pydantic v2** (`BaseModel`, `Field`) for all data structures.
- **Formatting & Linting:** Follow `ruff` defaults (PEP 8, 100-char line length).
- **Error Handling:** Never use bare `except:`. Catch specific exceptions, log structured context using Python's `logging` or `structlog`, and return graceful fallback scores if an external model fails.
- **Deterministic Seeding:** Set explicit random seeds (`random.seed(42)`, `np.random.seed(42)`) in all clustering and simulation scripts so hackathon demos and unit tests are 100% reproducible.

### 3.2 TypeScript & React Frontend (`frontend/`)
- **Framework:** Next.js 14+ (App Router), React 18+, TypeScript (`strict: true`). No `any` types allowed; define all interfaces in `src/types/chakravyuh.ts`.
- **Styling:** Tailwind CSS using the dark-mode tactical palette defined in `design.md`.
- **Performance:** Network graphs (`D3.js` / `Cytoscape`) and geospatial maps (`Deck.gl`) must use Canvas/WebGL rendering or debounced state updates when rendering $>200$ nodes to prevent React re-render freezes.

---

## 4. Ethical OSINT & Privacy Guardrails

1. **Public Data Only:** Never implement scrapers that bypass authentication walls, access private direct messages, or harvest non-public personal data.
2. **Organic User PII Protection:** For accounts classified as `ORGANIC_USER` (Bot Score $< 30$ and Sync Score $< 0.35$), support an automatic handle anonymization toggle (`@Citizen_Hash_8a2f`) in UI views and exported PDFs to protect innocent bystanders.
3. **No Automated Takedown Execution:** Chakravyuh is a **Decision Support & Early Warning System**. Always keep a "Human-in-the-Loop" confirmation step before dispatching external incident webhooks or official reports.

---

## 5. Workflow & Documentation Synchronization Rules

1. **Read Context First:** Before starting any coding task, read `memory.md` to check current architectural state and `tasks.md` to identify the active task.
2. **Update Living Docs:** Whenever a feature or module is completed:
   - Mark the corresponding checkbox `[x]` in `tasks.md`.
   - Record any new architectural decision, threshold tweak, or schema change in `memory.md`.
3. **Test Before Marking Done:** Every new analytical module in Layers 2–6 must include a self-contained test case verifying its output schema and edge cases (e.g., empty graph, single-node cluster, corrupted media file).
