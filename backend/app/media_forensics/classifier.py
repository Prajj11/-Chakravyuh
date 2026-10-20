"""Optional local safetensors image classifier; no automatic model download or remote code."""

import json
from pathlib import Path
from typing import Any

from PIL import Image

from app.evidence.canonical import canonical_bytes, sha256


class ImageClassifier:
    def __init__(self, directory: Path) -> None:
        manifest = json.loads((directory / "detector.json").read_text(encoding="utf-8"))
        self.model_id = str(manifest["model_id"])
        self.positive_label = str(manifest["positive_label"])
        if manifest["task"] not in {"ai_generated_image", "face_manipulation"}:
            raise ValueError("Image classifier task must describe its supported domain")
        self.task = str(manifest["task"])
        expected = manifest["files"]
        actual = {
            path.relative_to(directory).as_posix(): sha256(path.read_bytes())
            for path in directory.rglob("*")
            if path.is_file() and path.name != "detector.json"
        }
        if not expected or expected != actual:
            raise ValueError("Local model files do not match the detector manifest hashes")
        if any(name.endswith((".bin", ".pt", ".pth", ".pkl", ".py")) for name in actual):
            raise ValueError("Only safetensors models without custom Python code are supported")
        self.revision = sha256(canonical_bytes(manifest))
        try:
            from transformers import AutoImageProcessor, AutoModelForImageClassification
        except ImportError as exc:
            raise ValueError(
                "Install the optional nlp dependencies before configuring a model"
            ) from exc
        self.processor = AutoImageProcessor.from_pretrained(
            directory, local_files_only=True, trust_remote_code=False
        )
        self.model = AutoModelForImageClassification.from_pretrained(
            directory, local_files_only=True, trust_remote_code=False, use_safetensors=True
        )
        self.model.eval()
        self.model.to("cpu")
        labels = self.model.config.id2label
        if len(labels) != 2 or list(labels.values()).count(self.positive_label) != 1:
            raise ValueError("Classifier must have two explicitly named labels")
        self.positive_index = next(i for i, label in labels.items() if label == self.positive_label)

    def score(self, image: Image.Image) -> float:
        import torch

        inputs: Any = self.processor(images=image, return_tensors="pt")
        with torch.inference_mode():
            scores = self.model(**inputs).logits.softmax(dim=-1)[0]
        value = float(scores[self.positive_index]) * 100
        if not 0 <= value <= 100:
            raise ValueError("Model produced an invalid score")
        return value
