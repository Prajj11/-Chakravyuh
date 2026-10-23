# Current feature and crawler audit

Reviewed October 23, 2026 against `C:/Users/prajw/Downloads/Cluade.docx`. The document is an older assessment, not an execution specification. Its suggested work was assessed against current source code and local evidence. The project is still a prototype, but the claim that it has no public collectors is now outdated.

## Feature comparison

| Requirement or gap in the Word file | Current status and evidence |
|---|---|
| Public OSINT collection | Implemented, limited. `backend/app/ingestion/live.py` polls Hacker News, YouTube top-level comments for a configured video, Reddit submissions for a configured subreddit, and X recent search. HN was tested over the real network in this audit. Other platforms require credentials and remain unverified against live accounts here. |
| Telegram / Instagram collection | Absent. YouTube reply threads, Reddit comments, full repost acquisition and remote media downloads are also absent. |
| Text/narrative analysis | Present: frozen TF-IDF fallback, phrase-based harm indicators and claim retrieval/review in `nlp_engine`. A local multilingual transformer adapter exists. No configured text model or default local model directory was found in this environment; it remains fallback analysis. |
| Coordinated-account detection | Present: repeated content-linked timing, bot indicators, graph communities and role heuristics. These are not a trained/calibrated bot classifier or proof of disinformation. Real campaign detection accuracy is unvalidated. |
| Network/narrative propagation | Present: observed seeds, interaction graph, clusters and propagation views. Source coverage limits observable edges; roles do not establish global origin or intent. |
| Images | ELA/pHash present. A local safetensors image-classifier adapter now exists in `media_forensics/classifier.py`, but no image model is configured here and no validated deepfake weights are bundled. |
| Audio/video | Partially implemented since the Word assessment: MP4 frame sampling and 16-bit PCM WAV signal diagnostics in `media_forensics/av.py`. These are not audio/video deepfake detection. MP3 and C2PA verification remain unsupported. |
| Geography | H3, source/subject distinctions and baseline-dependent anomalies remain implemented. The gazetteer still has five cities; HN collection provides no reliable author coordinates. Real geographic anomaly accuracy is unvalidated. |
| Dashboard and early warnings | Present locally: campaign/graph/timeline/map/media/review/export views, collector status and gated alerts. Public polling now feeds the existing analysis pipeline. |
| External alert delivery | An optional signed webhook outbox with retries exists in `reporting/delivery.py`. Native email/SMS remain absent. No external webhook was sent during this audit. |
| Real-data evaluation | A supervised text baseline and recorded LIAR evaluation now exist. Recorded test F1 is 63.37% versus 60.34% for constant-positive prediction, with 47.21% precision. This is English statement classification, not Bihar campaign/bot/deepfake validation; it was not retrained in this audit. |
| Data beyond three synthetic scenarios | Original scenarios, an additional 25-case synthetic pack, and 10,084 collected HN records exist. The historical corpus remains separate from automatic dashboard import; live HN polling is integrated. Only 187 historical records explicitly mention Bihar. |
| Streaming / production performance | Bounded polling exists, not an exhaustive stream. Recorded 1,000-node warm graph median remains approximately 834 ms against the 800 ms target. No new throughput benchmark was performed. |
| Deployment and accounts | Local workbench; no multi-user identity/permissions deployment or Docker packaging found. Current local access no longer uses the older per-launch token flow. CI configuration exists; remote CI results were not checked. |
| Archive browser | CLI archive search exists; a dedicated archive UI remains absent. |

## Crawler defects fixed

1. **Unrelated HN results:** live search used fuzzy/prefix matching and accepted returned records without checking their own text. A real pre-fix `Bihar` query returned 100 records with zero whole-term Bihar matches. Search now disables fuzzy/prefix expansion, restricts searchable fields and requires a normalized whole-term phrase match in the item's own title/body. Parent titles, author names and linked URLs alone do not qualify.
2. **Lost story titles:** a story body previously replaced its title during normalization. Both are now retained for matching and analysis.
3. **Malformed rows stopped an entire poll:** invalid individual records are now skipped with an aggregate warning; valid records keep their original raw response pointers. Invalid response containers still fail the poll.
4. **Repeated cursor requests:** cursor-based adapters stop when a pagination token repeats, within the existing page limits.
5. **Duplicate ingestion after refresh failure:** if evidence was committed before analysis failed, the next poll now reuses the original stored event instead of creating another event when API counters or content changed. The normal first-seen deduplication policy remains in force.
6. **Blank queries:** whitespace-only and quote-only queries are rejected before collection.
7. **Missing documented launcher:** `start-live.bat` is restored as a compatibility wrapper for the existing integrated `start.bat`. The user's existing launcher was not rewritten.

Existing immutable evidence was not deleted or rewritten. The stricter matching affects future collection. For a clean comparison against a previously polluted live scope, use a new feed ID and retain the old evidence separately.

## Verification and limits

- Real corrected HN query: 100 returned records, all 100 matching Bihar in their own text; all 100 ingested through the analysis pipeline into an isolated temporary evidence store, with one campaign produced under the current observation window.
- Repeat of the same captured page: zero newly ingested records. Evidence integrity verification passed.
- Historical dataset verification: all 10,084 records and 617 raw responses passed reconstruction/hash checks.
- All 25 focused tests passed in 9.52 seconds, covering live collection, historical collection, media adapters, delivery and supervised evaluation. Repository type checking passed across 53 source files.
- Ruff passed for changed Python files. Type checking uses the repository's configured `--ignore-missing-imports` option; optional ML dependencies and third-party stubs are not all installed.

Machine-readable network result: [crawler audit](../evaluation/results/crawler-audit-2026-10-23.json).

These checks establish that the corrected HN path works for the tested sample. They do not justify saying every platform works perfectly. Authentication/quota failures, bounded sampling gaps, changes to external APIs, unsupported collection types, and lack of real task-specific ground truth remain material limitations. GUI rendering and full launcher startup were not exercised in this audit.
