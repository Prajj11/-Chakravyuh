# Public keyword corpus: collection result

Completed and verified October 19, 2026. User confirmed public collection using the organizer's supplied terms is allowed. The input files remain unchanged.

| Measure | Result |
|---|---:|
| Unique public records | 10,084 |
| Distinct public author usernames | 5,821 |
| Comments | 8,360 |
| Stories/posts | 1,724 |
| Distinct normalized text hashes | 9,962 |
| Records explicitly mentioning Bihar | 187 |
| Retained and verified API responses | 617 |
| Available ground-truth labels | 0 |

The source is Hacker News, collected through its public Algolia search API. Observed post timestamps range from January 3, 2020 through October 18, 2026. The initial target was 10,000; the final request completed its full page, yielding 10,084. Thirty query/time-window jobs remain available for continuation. This is a bounded convenience sample, not an exhaustive archive.

## Topic coverage

| Matched supplied term | Records |
|---|---:|
| phishing | 5,027 |
| ransomware | 4,007 |
| bank fraud | 234 |
| mass movement | 197 |
| bihar | 187 |
| online fraud | 145 |
| mass protest | 111 |
| public protest | 86 |

Terms can overlap in a record; these counts are not mutually exclusive classes. Broad phrases may have meanings unrelated to the intended Bihar context. Topic matches are retrieval evidence only. The corpus is predominantly cybersecurity discussion and cannot be presented as 10,084 Bihar incidents or confirmed disinformation examples.

## Files and verification

- `public_hn/posts.jsonl`: full corpus, SHA-256 `0be9f2298a6f764b3cbb32f71c7a517f4a31111b21618d5c1820c1031500df89`.
- `public_hn/posts_bihar_mentions.jsonl`: 187-record subset, SHA-256 `6d11201a107adf85bdc9eda42bc0e6dda8321dc4db22be29d2fa6caa84d776b7`.
- `public_hn/summary.json`: machine-readable coverage and collection state.
- `public_hn/raw/`, `captures.json`, `keywords.json` and `collection.sqlite3`: source responses, input hashes, exact response pointers and resumable checkpoints.

The verifier reproduced all 10,084 records from their retained source responses, checked 617 raw-response hashes, checked export uniqueness/counts and verified exact Bihar-subset membership. Four focused tests passed for keyword precision, source reconstruction/corruption detection, deduplication/checkpoints, time-window partitioning and rate-limit pausing. Ruff and mypy passed for the collector.

Original synthetic cases were preserved. Public corpus files remain local and are excluded from Git. See [collection instructions](README.md) to reproduce verification or resume toward a larger target.

## Readiness

The dataset is available for text exploration, topic clustering and limited conversation analysis. It is unlabelled, has no downloaded media bytes or reliable author geography, and is not imported into the dashboard. No detector was trained on it. Bihar-focused competition evaluation still needs stronger relevant source coverage and reviewed ground truth; this general corpus alone does not resolve that requirement.
