# Raw source fixtures

`backend/app/ingestion/simulator.py` generates seed-qualified raw SourceEvent observations
for three scenarios: electoral amplification (108 events), geographic mismatch (45) and
natural discussion (75), at seed 42. Accounts have repeated event-time observations and
approximately 25% missing profile/location metadata. No target scores or analytical roles
enter ingestion. Synthetic content and advisories are explicitly labelled.

`media/` contains generated baseline/spliced JPEG bytes. Recreate them with
`python backend/scripts/generate_fixtures.py`. `evaluation/spliced-mask.png` is a separate
localization ground-truth mask, read only by evaluation. It is not an engine input.

`registries/` holds retained synthetic advisory snapshots, known-claim entries, English/Hindi/
Hinglish harm phrases, a regional gazetteer and a frozen training corpus. Historical replay
generates raw observations in 240 covered hourly buckets; baseline counts are computed from
those observations, including covered zero-count hours. None contains a target Z score.

`raw/local-example.json` is a clearly USER_INJECTED CLI example. Run it with
`python -m app.cli ingest sample_data/raw/local-example.json`; repeat ingestion is idempotent.
All runtime evidence and analytical results live under the gitignored `.runtime/` directory.
Held-out split generators and recorded metrics are described in `evaluation/README.md`.
