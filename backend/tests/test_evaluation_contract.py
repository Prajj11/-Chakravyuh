import json
from pathlib import Path

from app.config import Parameters
from app.evaluation.dataset import build_split, split_manifest
from app.evidence.canonical import canonical_bytes


def test_evaluation_splits_are_disjoint_and_annotations_never_enter_source_events() -> None:
    splits = {name: build_split(name) for name in ("train", "calibration", "test")}
    manifests = {name: split_manifest(cases) for name, cases in splits.items()}
    for left, right in (("train", "calibration"), ("train", "test"), ("calibration", "test")):
        for key in ("families", "templates", "seeds", "account_ids"):
            assert not set(manifests[left][key]) & set(manifests[right][key])
    for cases in splits.values():
        raw = canonical_bytes([source for case in cases for source in case.sources])
        assert b"expected_coordination" not in raw and b"high_bot_indicator_accounts" not in raw


def test_committed_holdout_matches_frozen_parameters_and_dataset_without_rescoring() -> None:
    root = Path(__file__).resolve().parents[2]
    report = json.loads((root / "evaluation/results/heldout-v1.json").read_text(encoding="utf-8"))
    freeze = json.loads(
        (root / "evaluation/results/heldout-v1.freeze.json").read_text(encoding="utf-8")
    )
    assert report["parameter_set_id"] == freeze["parameter_set_id"] == Parameters().parameter_set_id
    for split in ("train", "calibration", "test"):
        assert (
            split_manifest(build_split(split))["dataset_sha256"]
            == freeze["splits"][split]["dataset_sha256"]
        )
