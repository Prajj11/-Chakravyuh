# Recorded evaluation and timing

These reports describe a small local demonstration release, not representative real-world
accuracy. Settings were frozen on calibration before the held-out test was scored once.
The test has not been rescored to tune thresholds. Performance work subsequently changed
equivalent graph execution, privacy transformation and evidence I/O, not analytical thresholds.

## Frozen synthetic evaluation

[`results/heldout-v1.freeze.json`](results/heldout-v1.freeze.json) records the parameters,
training corpus, split identities and calibration results before test execution.
[`results/heldout-v1.json`](results/heldout-v1.json) records test rows, missingness, per-language
metrics, dataset hashes and mask localization. Raw generator inputs contain no expected scores
or roles; labels and the image mask are separate evaluation inputs.

| Split | Cases | Topic families | Seeds | Dataset SHA-256 |
|---|---:|---|---|---|
| Train | 45 | agriculture, railway, sports | 11–13 | `46ece118e1e716ed7d5bca8eeaceb0d9ae104c6981e227eecd5c9ab7a24fa020` |
| Calibration | 45 | cinema, energy, heritage | 21–23 | `8f42d839fad617662e70bbaedeb535f90988823fd97bc30620b85cc4702fd24d` |
| Test | 45 | library, school, water | 31–33 | `ed4ffbe90b8977a6eb69c4bc409e183114ec5018ece2f4c4e3fd6c448903375d` |

Each split has repeated-copy coordination, benign coordinated mobilisation, ordinary viral
discussion, unique observations and intentionally insufficient history, across English, Hindi
and Hinglish. Account IDs, template sets, seeds and topic families are disjoint between splits.
The evaluation fallback vocabulary fits train only. Hindi/Hinglish examples use bilingual
synthetic templates, so this does not validate general monolingual semantic understanding.

| Measure | Calibration | Held-out test |
|---|---:|---:|
| Labelled coordination cases | 36 | 36 |
| Precision | 0.75 | 1.00 |
| Recall | 1.00 | 1.00 |
| F1 | 0.8571 | 1.00 |
| True / false positives / false negatives | 18 / 6 / 0 | 18 / 0 / 0 |
| Insufficient primary campaign results, of 45 | 21 | 27 |
| Gated alerts on benign mobilisation, of 9 | 0 | 0 |

The detector predicts whether any sufficiently qualified cluster establishes repeated
coordination. Benign mobilisation is coordination-positive and alert-negative ground truth.
Intentionally insufficient-history cases have no binary ground truth and are excluded from
F1. Negative cases without a qualifying cluster count as negative detector outcomes; the
27/45 insufficient primary results must therefore accompany the reported F1. High bot
indicators on volunteers would not establish automation or malicious intent.

Test F1 is 1.00 in each language on 12 labelled cases, with 9/15 insufficient primary results
and zero alerts among three benign mobilisation cases per language. These small counts,
synthetic construction and calibration false positives limit conclusions. No bot-classifier
accuracy, pretrained-model accuracy or production specificity is claimed.

ELA localization IoU is **1.00**, with one detected region on one reserved synthetic splice
mask. This exploratory case does not establish image-forgery accuracy. ELA measures compression
anomalies and can respond to benign processing. The mask is never an engine input.

- Parameter set: `475d31789d485a11d2128556a8bfbf16122e3d730a95f707091be36078747d8a`
- Training corpus: `c97b681643532b135cffeff439d118092293265bc7dab58e5e71d4858ec43568`
- TF-IDF revision: `tfidf-v1:1b285a21a7b4db67a6f94ed0c1828992acb792c86a0eb9b7c29d4c65ef54ac4b`
- Mask: `fdc53f916bebeb2d57f32b030ac6329c334ed170f78e67500cf3a2b1b0f7072d`
- Spliced JPEG: `e5d9e867e4c4c4ad64566e80ed0f872a46289f756fcad40b3987216401f62c96`
- Integrity at evaluation: 1,260 events, 3,784 artifacts, 1,261 audit entries verified.

The original command was:

```powershell
.\.venv\Scripts\python.exe -m app.evaluation --output evaluation/results/heldout-v1.json
```

The harness refuses to overwrite the output or its freeze record. Reproduction must use a new
output filename and preserve the original report. A repetition is not a new unseen test;
meaningful future accuracy claims need new untouched test families. Contract tests validate
split separation and frozen hashes without rescoring the held-out cases.

## Local performance

[`performance-v1.json`](results/performance-v1.json) retains the initial measurements.
[`performance-v2.json`](results/performance-v2.json) retains measurements after bounded
per-verification byte caching, compiled privacy replacement and exact native Brandes execution.
Every verification still rehashes all registered bytes; caches never carry across calls.
Rustworkx exact sequential directed betweenness is parity-tested against NetworkX to 1e-12.
NetworkX Louvain, its deterministic seed and all thresholds are unchanged.

Windows 11, AMD64 Family 25 Model 116 Stepping 1 (AuthenticAMD), 16 logical CPUs,
Python 3.12.10. Scoring/export use 100 events, one retained JPEG and no history. Graph workload
is a directed chain of 1,000 nodes / 999 reply edges, including exact betweenness, Louvain,
role assignment and typed output construction. Timings exclude fixture capture. Pipeline
initialization is separately reported as 37 ms. Cold means first operation in this process;
warm uses loaded code/models/fonts and operating-system caches.

| Operation | v1 warm | v2 cold | v2 warm | v2 warm maximum | Target |
|---|---:|---:|---:|---:|---:|
| Score 100 events, median (5 warm runs) | 562 ms | 491 ms | 425 ms | 513 ms | <2,000 ms |
| Verify/export 100 events, median (5) | 3,047 ms | 877 ms | 719 ms | 766 ms | <2,000 ms |
| Detail read P95 (30) | 26 ms | 102 ms | 26 ms | 28 ms | <200 ms |
| Graph 1,000 nodes, median (3) | 2,243 ms | 884 ms | 834 ms | 895 ms | <800 ms **unmet** |

REST uses an in-process ASGI TestClient, excluding TCP, browser and queue wait. These are
small sample measurements on local synthetic workloads. No 5,000-node browser or sustained
500-events/second claim is made. Native graph execution improved latency substantially but
did not meet the 800 ms target on this machine.

```powershell
.\.venv\Scripts\python.exe -m app.evaluation.benchmark --output evaluation/results/performance-new.json
```

The benchmark refuses overwrites. Keep previous measurements and report changes in workload,
hardware and cold/warm conditions. Do not change analytical definitions to improve a timing.
