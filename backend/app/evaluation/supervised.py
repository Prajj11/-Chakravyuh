"""Train and independently evaluate a labelled text baseline without pickle model loading.

JSONL rows: id, text, label (0/1), group (author/campaign family), provenance, language.
Use train/calibration/test files from a documented, legitimately obtained labelled dataset.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from scipy.special import expit
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from app.evidence.canonical import canonical_bytes, sha256

FEATURES = 16384


class LabelledText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    label: int = Field(ge=0, le=1)
    group: str = Field(min_length=1)
    provenance: str = Field(min_length=1)
    language: str = Field(min_length=1)


def vectorizer() -> HashingVectorizer:
    return HashingVectorizer(
        analyzer="char",
        ngram_range=(3, 5),
        n_features=FEATURES,
        alternate_sign=False,
        norm="l2",
        lowercase=True,
    )


def load(path: Path) -> list[LabelledText]:
    rows = [
        LabelledText.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) < 4 or {row.label for row in rows} != {0, 1}:
        raise ValueError("Every split needs at least four rows and both labels")
    if len({row.id for row in rows}) != len(rows):
        raise ValueError("Duplicate row IDs within split")
    return rows


def ensure_disjoint(splits: list[list[LabelledText]]) -> None:
    for key in ("id", "group", "text"):
        seen: set[str] = set()
        for rows in splits:
            values = {
                " ".join(row.text.casefold().split()) if key == "text" else str(getattr(row, key))
                for row in rows
            }
            if seen & values:
                raise ValueError(f"Dataset leakage across splits: {key}")
            seen.update(values)


def metrics(labels: list[int], scores: np.ndarray, threshold: float) -> dict[str, Any]:
    predictions = scores >= threshold
    return {
        "n": len(labels),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "brier": float(brier_score_loss(labels, scores)),
        "average_precision": float(average_precision_score(labels, scores))
        if len(set(labels)) == 2
        else None,
        "confusion_matrix_labels_0_1": confusion_matrix(
            labels, predictions, labels=[0, 1]
        ).tolist(),
    }


def train(
    train_file: Path, calibration_file: Path, test_file: Path, output: Path, task: str
) -> dict[str, Any]:
    if output.exists():
        raise ValueError("Output already exists; use a new experiment directory")
    training, calibration, testing = [load(p) for p in (train_file, calibration_file, test_file)]
    ensure_disjoint([training, calibration, testing])
    encoder = vectorizer()
    model = LogisticRegression(C=1, max_iter=1000, random_state=42)
    model.fit(encoder.transform([r.text for r in training]), [r.label for r in training])
    cal_scores = model.predict_proba(encoder.transform([r.text for r in calibration]))[:, 1]
    thresholds = [i / 100 for i in range(5, 96)]
    threshold = max(
        thresholds, key=lambda t: (f1_score([r.label for r in calibration], cal_scores >= t), t)
    )
    weights = {
        "format": "hash-char-logistic-v1",
        "task": task,
        "n_features": FEATURES,
        "weights": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
        "threshold": threshold,
        "training_sha256": sha256(train_file.read_bytes()),
    }
    scores = model.predict_proba(encoder.transform([r.text for r in testing]))[:, 1]
    report = {
        "task": task,
        "threshold_selected_on": "calibration",
        "threshold": threshold,
        "model_sha256": sha256(canonical_bytes(weights)),
        "dataset_sha256": {
            name: sha256(path.read_bytes())
            for name, path in zip(
                ("train", "calibration", "test"),
                (train_file, calibration_file, test_file),
                strict=True,
            )
        },
        "test": metrics([r.label for r in testing], scores, threshold),
        "test_constant_positive_baseline": metrics(
            [r.label for r in testing], np.ones(len(testing)), 0.5
        ),
        "by_language": {
            language: metrics(
                [r.label for r in testing if r.language == language],
                scores[[r.language == language for r in testing]],
                threshold,
            )
            for language in sorted({r.language for r in testing})
        },
        "limitations": [
            "Measures only the supplied binary text label, not coordinated campaign detection.",
            "Labels and provenance require independent review of the dataset owner's assertions.",
            "Not a calibrated probability of truth or account automation.",
            "No deployment claim; domain shift and near-duplicate leakage require further review.",
        ],
    }
    output.mkdir(parents=True)
    (output / "model.json").write_bytes(canonical_bytes(weights))
    (output / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def predict(model_file: Path, texts: list[str]) -> list[float]:
    model = json.loads(model_file.read_bytes())
    if model["format"] != "hash-char-logistic-v1" or model["n_features"] != FEATURES:
        raise ValueError("Unsupported text model format")
    weights = np.asarray(model["weights"], dtype=float)
    if weights.shape != (FEATURES,) or not np.isfinite(weights).all():
        raise ValueError("Invalid model weights")
    intercept = float(model["intercept"])
    if not np.isfinite(intercept):
        raise ValueError("Invalid model intercept")
    return expit(vectorizer().transform(texts) @ weights + intercept).tolist()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", required=True, help="Exact meaning of binary label 1")
    args = parser.parse_args()
    print(
        json.dumps(train(args.train, args.calibration, args.test, args.output, args.task), indent=2)
    )


if __name__ == "__main__":
    main()
