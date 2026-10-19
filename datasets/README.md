# Organizer keywords and public collection

The original `Hashtags .txt` and `hashtags2.txt` are keyword/query specifications. The user confirmed on October 19, 2026 that the organizers allow public collection using these lists.

## Public corpus

`public_hn/` contains a locally collected, unlabelled sample of Hacker News stories and comments obtained through its public Algolia search API. It is a staging dataset, not yet imported into the investigation dashboard. The dashboard does not currently have a Hacker News platform adapter.

Collection uses only terms extracted from the two original files. It applies Unicode normalization and case folding, disables fuzzy/prefix search, then requires a whole-term match in each item's own title/body. Matches in author names, linked URLs or parent-story titles alone are rejected. Original text and response bytes are retained separately from normalized matching text. No synonyms or generated posts are added.

This source is stronger for generic cybersecurity terms than Bihar-specific Hindi discourse. A record matching `phishing` or `ransomware` need not concern Bihar. The sample contains ordinary discussion and must not be presented as a collection of confirmed disinformation campaigns. The report lists observed term counts so source bias is visible.

Files in `public_hn/`:

| File | Purpose |
|---|---|
| `posts.jsonl` | One normalized public story/comment per stable platform ID |
| `posts_bihar_mentions.jsonl` | Subset whose own text explicitly mentions Bihar in English or Hindi; this does not establish author location |
| `keywords.json` | Input hashes and normalized terms linked to input filenames |
| `raw/<sha256>.json` | Exact search-response bytes |
| `captures.json` | Request URLs, capture timestamps, response hashes and page counts |
| `collection.sqlite3` | Resumable query checkpoints, posts and all capture observations |
| `summary.json` | Actual counts, coverage, collection status and export checksum |
| `last_error.json` | Most recent paused request, if one occurred; historical after resuming |

Raw and normalized collected content stays local and is excluded from Git. Code and this guide can be committed independently. Keep the complete folder when preserving evidence: `posts.jsonl` alone cannot verify original response bytes.

## Run or resume

From the repository root in PowerShell:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m app.ingestion.public_dataset --target 10000 --max-requests 1800
```

Rerunning resumes the same fixed time window and checkpoints. Increase `--target` to collect more available matches. Use a different `--output` directory for a new collection window or modified keyword inputs. The default start date is January 1, 2020; the upper bound is captured at collection creation. A target is a stopping condition, not a guaranteed available record count. Collection stops at a page boundary, so it may exceed the target by at most 99 posts.

```powershell
..\.venv\Scripts\python.exe -m app.ingestion.public_dataset --verify
```

Verification checks organizer input hashes, raw-response hashes, exported IDs and counts, and recomputes every normalized record from its exact raw response pointer.

The collector pauses on HTTP errors, including 403/429, or network/response failures. It retains the pending page for resumption. Inspect `last_error.json` and respect any retry interval before restarting. It does not rotate hosts or bypass blocks. It uses a fixed allowlisted endpoint with redirects disabled and a minimum 0.5-second delay between completed requests. Larger query sets are divided into non-overlapping time windows to respect search pagination depth.

## Analysis limitations

The corpus records observed post IDs, text, public usernames, timestamps, source URLs, available reply/thread IDs and engagement fields. Unknown language, author location and labels stay null. Story/comment links can refer to items outside the collected sample. Distinct post IDs with identical text remain separate because repetition can be analytically relevant; `text_sha256` permits grouping duplicates for evaluation splits.

There are no verified bot, coordination or disinformation labels, media bytes, or reliable author geographic coordinates. This corpus supports ingestion experiments, topic grouping and limited observed conversation analysis. It does not establish supervised detection accuracy or validate deepfake/geospatial detectors. Group future evaluation splits by thread/account and identical text as appropriate to avoid leakage.

Sources: [HN public API](https://github.com/HackerNews/API), [HN Search API](https://hn.algolia.com/api), [search implementation](https://github.com/algolia/hn-search).
