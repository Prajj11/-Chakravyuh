import json
from pathlib import Path

import pytest

from app.evaluation.supervised import LabelledText, ensure_disjoint, predict, train


def test_rejects_cross_split_author_and_normalized_duplicates() -> None:
    row = LabelledText(
        id="1", text="Message  ONE", label=0, group="author", provenance="fixture", language="en"
    )
    with pytest.raises(ValueError, match="group"):
        ensure_disjoint([[row], [row.model_copy(update={"id": "2", "text": "different"})]])
    with pytest.raises(ValueError, match="text"):
        ensure_disjoint(
            [[row], [row.model_copy(update={"id": "2", "group": "other", "text": " message one "})]]
        )


def test_training_safe_model_roundtrip_and_frozen_output(tmp_path: Path) -> None:
    paths = []
    for split in ("train", "cal", "test"):
        path = tmp_path / f"{split}.jsonl"
        path.write_text(
            "\n".join(
                json.dumps(
                    {
                        "id": f"{split}-{i}",
                        "group": f"{split}-author-{i}",
                        "text": f"{split} {i} " + ("danger fraud" if i % 2 else "library books"),
                        "label": i % 2,
                        "provenance": "TEST_FIXTURE_NOT_ACCURACY",
                        "language": "en",
                    }
                )
                for i in range(8)
            ),
            encoding="utf-8",
        )
        paths.append(path)
    output = tmp_path / "experiment"
    report = train(*paths, output, "unit-test-only")
    assert report["test"]["n"] == 8
    values = predict(output / "model.json", ["library books", "danger fraud"])
    assert 0 <= values[0] < values[1] <= 1
    with pytest.raises(ValueError, match="already exists"):
        train(*paths, output, "unit-test-only")
