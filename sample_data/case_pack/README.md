# Diverse synthetic case pack

25 fictional cases, **7,500 posts**, **1,500 distinct accounts**, **25 cities**.
Each case contains 300 posts from 60 accounts across five observation waves.
The pack has 2,500 English, 2,500 Hindi and 2,500 Hinglish posts.

## Load into the dashboard

1. Start/restart the backend and frontend after installing this update.
2. Connect with the current local launch token and open **Scenario studio**.
3. Choose **25 diverse cases · 7,500 posts**, or an individual city/case.
4. Leave **Fast batch load** enabled, then click **Load raw scenario**.
5. Wait for **Replay completed**; select a detected narrative from the queue.

Fast loading skips wall-clock playback delays and analyses each complete case with the real
pipeline. It preserves event timestamps and publishes one notification per processed case;
intermediate warning times are not reconstructed. Disable fast loading for timed playback.
At 100× speed, the longest case still represents several minutes of playback. Reset replaces
active replay generations; uncheck it to retain the current replay alongside another case.
Injections and retained evidence follow the existing reset rules.

Source cases are generation scopes, not predefined detected campaigns. The local lexical
fallback can split a case into language/content variants. The queue's narrative count can
therefore exceed 25. All raw posts remain available through the computed snapshots within
their respective 24-hour narrative windows.

## What is included

| City | Exercise |
|---|---|
| Mumbai | Recycled flood photograph |
| Delhi | Unverified school closure notice |
| Bengaluru | Altered metro fare screenshot |
| Chennai | Water contamination claim |
| Kolkata | Fictional bank closure rumour |
| Hyderabad | Misattributed clinic message |
| Jaipur | Fictional exam paper leak |
| Ahmedabad | Impersonated electricity refund |
| Pune | Fuel shortage amplification |
| Kochi | Unverified cyclone voice-message transcript |
| Panaji | Outdated beach restriction notice |
| Bhopal | Fictional ration registration deadline |
| Patna | Mislocated bridge clip caption |
| Bhubaneswar | Conflicting evacuation route messages |
| Guwahati | Telecom shutdown rumour |
| Lucknow | Fictional polling-hours change |
| Surat | Blood donation volunteer mobilisation |
| Indore | Neighbourhood cleanup coordination |
| Nagpur | Food collection volunteer network |
| Thiruvananthapuram | Storm assistance coordination |
| Chandigarh | Independent bus service feedback |
| Dehradun | Independent park access discussion |
| Ranchi | Waste collection observations |
| Visakhapatnam | Harbour weather discussion |
| Coimbatore | Library opening-hours discussion |

The first 16 exercise content-amplification patterns; four exercise benign mobilisation;
five exercise ordinary discussion. These are authoring intentions, not predicted labels,
proof of falsity or held-out evaluation results. No expected score or analytical role is
stored in a source event. References use example.invalid and fictional institutions.

## Files and regeneration

- Each `demo_*.jsonl` contains 300 schema-valid SourceEvent rows, one JSON object per line.
- `manifest.json` records seed 42, file SHA-256 hashes, counts, cities, languages and time spans.
- `backend/app/ingestion/case_catalogue.py` defines the fictional stories and generation patterns.
- `backend/app/ingestion/case_pack.py` deterministically generates the observations. Runtime
  replay uses this same generator with the selected seed; these files are its seed-42 export.

From the repository root on Windows:

```powershell
.venv\Scripts\python.exe -m app.ingestion.case_pack
.venv\Scripts\python.exe -m app.ingestion.case_pack --check
```

The exporter also regenerates the frontend scenario menu. `--check` validates every exported
file and menu entry against the generator without modifying files. Parent references in raw
files use `source:<source_event_key>`; replay resolves them to retained event IDs in event-time
order. Use Scenario studio to analyse the files; the single-event CLI is not a pack loader.

## Evidence limits

All posts are visibly marked SYNTHETIC EXERCISE and have SYNTHETIC_REPLAY provenance.
Twenty percent of accounts lack location/profile observations; other locations mix synthetic
GPS and profile declarations. Some campaigns contain outside-city declarations. Missing
locations stay missing. Profiles and timestamps are synthetic, not observations of real people.

Seven cases reuse the repository's generated baseline/spliced JPEGs on a subset of posts;
these are generic forensic fixtures, not actual photographs of the depicted incident.
References to voice/video content are text-only: no audio/video bytes or detector results
are invented. There are no new historical geographic baselines or fact-check advisories,
so unavailable Z-scores and unverified claims remain visible. The earlier three scenarios
and their historical fixtures are still separately available.
