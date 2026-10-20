# Public collection and remaining validation work

This extension connects public API observations to the existing evidence, narrative,
coordination, graph, geo and campaign pipeline. It does not turn coordination indicators
into proof that a claim is false.

## Start on Windows

1. Stop existing backend/frontend consoles with Ctrl+C.
2. Double-click `start-live.bat`. On first launch it copies
   `live-feeds.example.json` to the git-ignored `live-feeds.local.json`.
3. Open http://127.0.0.1:3000 and connect with the current token from
   `.runtime/local-session-token`.
4. Expand **Public collection** to see polling state, last success, observation count,
   and webhook delivery counts. Public campaigns enter the normal campaign feed.
5. Edit `live-feeds.local.json` and restart to change topics. Default: one Hacker News
   keyword query, `phishing`, every 60 seconds, at most 100 newest matching results.
   This is a cybersecurity demonstration, not a Bihar-disinformation dataset.

`start.bat` retains the ordinary offline configuration unless live settings are supplied
in its environment. Both modes retain `sample_data`: it still supplies required resources.

## Supported API adapters

| platform | query | credential_env | Scope and limits |
|---|---|---|---|
| hacker_news | Search words | omit | Algolia public search; stories/comments, no key |
| youtube | One video ID | YOUTUBE_API_KEY | Official API, top-level comments only |
| reddit | One subreddit name | REDDIT_ACCESS_TOKEN | OAuth API, newest submissions only; renewable token supplied externally |
| x_twitter | Recent-search query | X_BEARER_TOKEN | Official API; account access/quota required |

For example, add this object to the configuration array:

```json
{
  "id": "youtube-video",
  "platform": "youtube",
  "query": "YOUR_VIDEO_ID",
  "credential_env": "YOUTUBE_API_KEY",
  "interval_seconds": 120,
  "max_pages": 2
}
```

Set that environment variable locally before launching. Never put the credential itself
in the JSON or commit it. HTTP errors cause exponential backoff, capped at one hour.
The interface reports failure type without exposing secret-bearing exception text.
Redirects are rejected. Responses are bounded to 5 MB per page.

Polling is a bounded sample, not an exhaustive archive or streaming firehose. Feed limits
are 10 feeds and 10 pages per poll. Busy feeds can have gaps. First-seen post identity is
persistently deduplicated; later edits/deletions are not synchronized by these adapters.
Collection coverage and GPS are not invented. Graph edges appear only when the adapter
provides enough evidence, e.g. X direct reply targets. YouTube replies, Reddit comments,
Telegram, platform-wide account histories, and remote media downloads are not implemented.
Use separate feed IDs for separate collection scopes. Cross-feed identity reconciliation
and cross-platform campaign merging remain future work.

References: [HN API](https://hn.algolia.com/api),
[YouTube comments](https://developers.google.com/youtube/v3/docs/commentThreads/list),
[Reddit API](https://www.reddit.com/dev/api/),
[X recent search](https://docs.x.com/x-api/posts/search-recent-posts).

## Alerts

Public campaigns use the existing CTI coverage and cooldown gates. Alerts publish to the
dashboard WebSocket and enter a durable SQLite outbox. Synthetic replay alerts never go
to the external delivery path.

To enable an existing webhook receiver, set `CHAKRAVYUH_ALERT_WEBHOOK_URL` (HTTPS) and
`CHAKRAVYUH_ALERT_WEBHOOK_SECRET` (at least 32 characters) locally and restart. No receiver
is configured by default. The receiver can route notifications to email/SMS, but native
email/SMS delivery is not implemented.

Payloads contain campaign IDs and assessments, not account handles or post text.
`Idempotency-Key` identifies duplicate deliveries. The HMAC SHA-256 signature covers
`X-Chakravyuh-Timestamp + "." + exact body bytes`, using the configured secret;
it is supplied in `X-Chakravyuh-Signature`. Receivers should verify signatures, reject stale
timestamps, and deduplicate keys. Delivery is at least once, not exactly once.
After eight failures an item is marked FAILED; status is available through
`GET /api/v1/alerts/delivery`. There is currently no UI retry/requeue action.
Keep the receiver stable while a backlog exists: the outbox uses the current destination.

## Media

JPEG/PNG/WebP retain ELA and pHash. MP4 upload now validates decoding and samples at most
12 frames in an isolated subprocess with a 25-second deadline. Videos are limited to
25 MiB, 24 million pixels and one hour. The report shows duration, frame rate and sampled
frame diversity. WAV diagnostics cover the first 60 seconds of 16-bit PCM, with RMS,
clipping ratio, duration and sample rate. Other WAV formats can remain retained but have
unavailable diagnostics.

These are signal measurements, not video/audio deepfake detection, lip-sync analysis or
proof of editing. Authenticity scores remain unavailable without a suitable model.

An optional **image-only** binary classifier can be configured with
`CHAKRAVYUH_IMAGE_MODEL_DIR`. It requires optional `nlp` dependencies (which supply
PyTorch/Transformers), a compatible local Hugging Face image-classification model in
safetensors format, processor files, and a `detector.json` manifest:

```json
{
  "model_id": "publisher/model-name",
  "task": "ai_generated_image",
  "positive_label": "exact-positive-label-from-config",
  "files": {
    "config.json": "SHA256_OF_FILE",
    "preprocessor_config.json": "SHA256_OF_FILE",
    "model.safetensors": "SHA256_OF_FILE"
  }
}
```

Use `face_manipulation` for a model trained on that task. List every model-directory file
except the manifest. Hash mismatches, pickle weights, custom Python code, unsupported
architectures and ambiguous labels are rejected. Loading is CPU-only and offline.
No model weights have been selected/downloaded or validated in this change.
Model output is supplementary and uncalibrated; CTI still uses the existing forensic
indicator. An image classifier is not a validated video detector.

## Real labelled benchmark and ML

`app.evaluation.supervised` trains logistic regression on hashed character features.
It accepts JSONL rows with `id`, `text`, binary `label`, speaker/campaign `group`,
`provenance`, and `language`. The exact meaning of label 1 must be provided with `--task`.
It rejects overlapping IDs, groups and normalized exact text across the three splits.
Threshold selection uses calibration only. Test results are written once into a new
experiment directory. Model artifacts are JSON numerical coefficients, never pickle.

The author-hosted [LIAR benchmark](https://aclanthology.org/P17-2067/) supplies actual
labelled statements. `app.evaluation.liar` downloads that archive and constructs a
**new speaker-disjoint split**, not the official benchmark split. Label 1 combines
`false`/`pants-fire`; label 0 combines `true`/`mostly-true`. Ambiguous middle labels are
excluded. This changes the task and must be disclosed when presenting results.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m app.evaluation.liar --output .runtime/datasets/liar-new
.\.venv\Scripts\python.exe -m app.evaluation.supervised `
  --train .runtime/datasets/liar-new/train.jsonl `
  --calibration .runtime/datasets/liar-new/calibration.jsonl `
  --test .runtime/datasets/liar-new/test.jsonl `
  --output .runtime/models/liar-new `
  --task liar_false_or_pants_fire_vs_true_or_mostly_true
```

The recorded first experiment used 6,729 training, 620 calibration and 692 test
statements. Test precision **47.21%**, recall **96.32%**, F1 **63.37%**;
constant-positive F1 **60.34%**. It produced 322 false positives and 11 false negatives.
This is not suitable as an automatic accusation or alert trigger, so it is **not enabled
in the campaign scoring pipeline**. The experiment is recorded separately from the
existing frozen synthetic evaluation.

This does not validate account automation, coordinated campaigns, India/Hindi/Hinglish,
geospatial alerts or media. Those need task-specific real labelled datasets, suitable
models and a separately frozen evaluation. No deployment accuracy is claimed.

## Remaining competition requirements

- Credentialed platform adapters still need live-account verification.
- Telegram and full reply/repost/media acquisition are absent.
- Trained bot detection, robust multilingual harm classification, deepfake image model
  selection/calibration, and audio/video deepfake models still require work.
- Public-feed latency/throughput and real campaign detection accuracy are unmeasured.
- Native email/SMS channels are absent; the webhook receiver can bridge them.
- This remains a local analyst workbench, not a hardened multi-user agency deployment.
