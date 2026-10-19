# Organizer input audit

Inspected October 19, 2026. This records input readiness and pending migration work; it does not claim a trained model or an implemented competition mode.

**Follow-up:** The user clarified that the two TXT files are all that was supplied and explicitly confirmed that public collection is allowed. A public Hacker News collection pipeline is now available; see [dataset guide](../datasets/README.md). Original input findings below remain valid. The separate-post-dataset question is resolved; training labels and competition dashboard integration remain outstanding.

## Supplied files

The `datasets/` directory currently contains exactly two files, both keyword/search-query lists:

| File | Bytes | SHA-256 |
|---|---:|---|
| `Hashtags .txt` | 6,344 | `fb18fc6cbacdd6c23591131e08b7e907a3c43eb07a627d3533464f7f1e4d3996` |
| `hashtags2.txt` | 7,683 | `6b0fcd9fdd0be5e8353c2885925d12d82be73e0db00be6196fbddfcc0cda2421` |

They cover Bihar-related topics, cybercrime, examinations/recruitment, floods, education, regional news and political discussion, using English and Hindi phrases, hashtags and Boolean OR expressions. Preserve these original bytes; any normalized search configuration should be a separate derivative. Review spelling and mixed-script lookalikes before using terms for retrieval.

There are no post records, account histories, posting timestamps, interaction edges, observed geographic metadata, media files or ground-truth labels. No collection instructions or dataset licence are included in this folder.

## What these inputs support

These lists can configure topic matching and, if the organizers permit collection, define search scope. A keyword match indicates topic relevance only. Political terms, locations, names and hashtags must not become suspiciousness or disinformation labels.

They cannot support supervised detector training, calibrated bot/deepfake probabilities, measured detection accuracy, coordination graphs, narrative propagation or geographic anomaly measurements. Fitting a vocabulary to keyword lists would not constitute training or evaluating a disinformation detector.

## Required next input

The user confirmed that these queries are intended for authorized public collection. No separate organizer post dataset has been supplied. Collect observed records using these terms and preserve their provenance; generated examples cannot substitute for collected evidence.

For supplied records, inspect the real schema before implementing an importer. Useful fields are stable post/account identifiers, text, platform, timestamps, interaction references and provenance; geographic and media analyses additionally require their corresponding evidence. Preserve missing fields as unavailable rather than fabricate them.

Supervised training requires suitable labels and documented label meaning. If only unlabelled records are supplied, scope the work to unsupervised grouping and explainable observed-behaviour indicators. Evaluate any trained models on held-out records with account/campaign and temporal leakage controls, and report class balance and false positives where labels permit.

## Synthetic-case recommendation and migration checklist

Exclude the original three scenarios and the 25-case / 7,500-post pack from competition training, evaluation and demonstrations. Retain a backup rather than permanently deleting the work; include development fixtures in a submission only if the organizers allow them.

The current application still exposes synthetic replay. The following work is pending, not implemented by this audit:

- Disable synthetic startup/replay and Scenario studio in the competition workflow, including backend entry points.
- Use a separate competition evidence store so existing `.runtime/` replay records cannot appear in competition outputs.
- Audit the synthetic training vocabulary, claim references, registries and fallback assets; exclude them from competition fitting and evidence retrieval, and establish whether external pretrained weights or reference resources are permitted.
- Import the actual authorized records with byte-level provenance and a reproducible input manifest.
- Adapt available dashboard panels to actual field coverage; show unavailable analyses explicitly.
- Train/evaluate only tasks supported by the records and labels. The earlier synthetic test results are software checks, not accuracy evidence on organizer data.

No source datasets or prior cases were deleted and no model was trained during the initial audit. Public collection was subsequently authorized and is recorded separately in the dataset guide and collection manifest.
