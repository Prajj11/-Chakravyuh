import json
from pathlib import Path

import pytest

from app.media_forensics.classifier import ImageClassifier


def test_unverified_model_files_rejected_before_loading(tmp_path: Path) -> None:
    (tmp_path / "model.safetensors").write_bytes(b"changed")
    (tmp_path / "detector.json").write_text(
        json.dumps(
            {
                "model_id": "fixture",
                "positive_label": "fake",
                "task": "ai_generated_image",
                "files": {"model.safetensors": "0" * 64},
            }
        )
    )
    with pytest.raises(ValueError, match="manifest hashes"):
        ImageClassifier(tmp_path)
