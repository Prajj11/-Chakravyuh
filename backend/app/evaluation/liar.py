"""Reproducible speaker-disjoint LIAR binary benchmark preparation (not official splits)."""

import argparse
import csv
import io
import json
import zipfile
from pathlib import Path
from urllib.request import urlopen

from app.evidence.canonical import canonical_bytes, sha256

URL = "https://sites.cs.ucsb.edu/~william/data/liar_dataset.zip"
LABELS = {"false": 1, "pants-fire": 1, "true": 0, "mostly-true": 0}


def prepare(output: Path) -> dict:
    if output.exists():
        raise ValueError("Dataset output already exists; preserve existing experiments")
    with urlopen(URL, timeout=30) as response:
        raw = response.read(5_000_001)
    if len(raw) > 5_000_000:
        raise ValueError("Unexpected archive size")
    splits: dict[str, list[dict]] = {"train": [], "calibration": [], "test": []}
    seen: set[str] = set()
    removed = 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for name in ("train.tsv", "valid.tsv", "test.tsv"):
            info = archive.getinfo(name)
            if info.file_size > 10_000_000:
                raise ValueError("Unexpected TSV size")
            for row in csv.reader(io.StringIO(archive.read(name).decode("utf-8")), delimiter="\t"):
                if len(row) < 5 or row[1] not in LABELS or not row[4].strip():
                    removed += 1
                    continue
                normalized = " ".join(row[2].casefold().split())
                if normalized in seen:
                    removed += 1
                    continue
                seen.add(normalized)
                speaker = row[4].strip().casefold()
                bucket = int(sha256(("liar-speaker-v1:" + speaker).encode()), 16) % 10
                split = "train" if bucket < 8 else "calibration" if bucket == 8 else "test"
                splits[split].append(
                    {
                        "id": row[0],
                        "text": row[2],
                        "label": LABELS[row[1]],
                        "group": speaker,
                        "provenance": f"LIAR/Wang2017/{name}/{row[0]}/{row[1]}",
                        "language": "en",
                    }
                )
    output.mkdir(parents=True)
    (output / "source.zip").write_bytes(raw)
    for name, rows in splits.items():
        (output / f"{name}.jsonl").write_bytes(
            b"\n".join(canonical_bytes(row) for row in rows) + b"\n"
        )
    manifest = {
        "source_url": URL,
        "paper": "https://aclanthology.org/P17-2067/",
        "archive_sha256": sha256(raw),
        "label_mapping": LABELS,
        "excluded": "half-true, barely-true, missing speakers, normalized exact duplicate text",
        "removed_rows": removed,
        "split": "sha256('liar-speaker-v1:' + normalized_speaker) mod 10; 0-7/8/9",
        "official_split_comparable": False,
        "counts": {name: len(rows) for name, rows in splits.items()},
        "groups": {name: len({row["group"] for row in rows}) for name, rows in splits.items()},
        "limitations": [
            "Historical US English political statements; not a social network campaign dataset.",
            "Research source attribution does not establish redistribution rights.",
            "Same topic or near-duplicate claims may span speakers; exact duplicates are removed.",
        ],
    }
    (output / "manifest.json").write_bytes(canonical_bytes(manifest))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(prepare(parser.parse_args().output), indent=2))
