"""Freeze on calibration, then evaluate the test split once without parameter tuning."""

import json
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image

from app.config import Parameters
from app.coordination.engine import CoordinationEngine
from app.evaluation.dataset import EvaluationCase, build_split, split_manifest
from app.evidence.canonical import canonical_bytes, sha256
from app.ingestion.service import IngestionService
from app.ingestion.simulator import fixture_root, media_bytes
from app.media_forensics.engine import MediaEngine
from app.nlp_engine.engine import NarrativeEngine
from app.pipeline import vector_similarity
from app.reporting.cti import compute_cti
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import AnalysisStatus, DataOrigin


def metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    labeled = [row for row in rows if row["expected_coordination"] is not None]
    tp = sum(
        row["predicted_coordination"] is True and row["expected_coordination"] is True
        for row in labeled
    )
    fp = sum(
        row["predicted_coordination"] is True and row["expected_coordination"] is False
        for row in labeled
    )
    fn = sum(
        row["predicted_coordination"] is False and row["expected_coordination"] is True
        for row in labeled
    )
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    benign = [row for row in rows if row["category"] == "benign_mobilisation"]
    return {
        "labeled_cases": len(labeled),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
        "benign_coordinated_cases": len(benign),
        "benign_alert_false_positives": sum(bool(row["alert_eligible"]) for row in benign),
        "insufficient_primary_results": sum(bool(row["all_clusters_insufficient"]) for row in rows),
    }


def evaluate(
    cases: tuple[EvaluationCase, ...], nlp: NarrativeEngine, repo: EvidenceRepository
) -> list[dict[str, object]]:
    rows = []
    p = repo.parameters
    for case in cases:
        events = [
            IngestionService(repo).ingest(source, scope="evaluation") for source in case.sources
        ]
        clusters = nlp.cluster(events, partition_id=case.case_id)
        predicted = False
        alert = False
        statuses = []
        high_bots = set()
        for cluster in clusters:
            members = [event for event in events if event.event_id in cluster.event_ids]
            vectors = nlp.embed([event.text for event in members])
            indices = {event.event_id: index for index, event in enumerate(members)}
            result = CoordinationEngine(p).analyze(
                members, similarity=partial(vector_similarity, vectors, indices)
            )
            statuses.append(result.assessment.analysis_status)
            predicted |= (
                result.assessment.sync_score is not None
                and result.assessment.sync_score >= p.BOT_SYNC_SCORE_CUTOFF
            )
            cti = compute_cti(p, members, result.assessment, result.bots, [], [], nlp.harm(members))
            alert |= cti.alert_eligible
            high_bots |= {
                author
                for author, bot in result.bots.items()
                if bot.bot_indicator_score is not None
                and bot.bot_indicator_score >= p.BOT_PROBABILITY_HIGH_CUTOFF
            }
        rows.append(
            {
                "case_id": case.case_id,
                "family": case.family,
                "language": case.language,
                "seed": case.seed,
                "category": case.category,
                "expected_coordination": case.expected_coordination,
                "predicted_coordination": predicted,
                "alert_eligible": alert,
                "all_clusters_insufficient": not any(
                    status == AnalysisStatus.AVAILABLE for status in statuses
                ),
                "cluster_count": len(clusters),
                "high_bot_indicator_accounts": len(high_bots),
                "missing_creation_ratio": sum(
                    source.account.created_at is None for source in case.sources
                )
                / len(case.sources),
            }
        )
    return rows


def run(output: Path) -> None:
    if output.exists() or output.with_suffix(".freeze.json").exists():
        raise FileExistsError("This held-out run already exists; outputs are never overwritten")
    output.parent.mkdir(parents=True, exist_ok=True)
    p = Parameters()
    splits = {name: build_split(name) for name in ("train", "calibration", "test")}
    manifests = {name: split_manifest(cases) for name, cases in splits.items()}
    for left, right in (("train", "calibration"), ("train", "test"), ("calibration", "test")):
        for field in ("families", "templates", "seeds", "account_ids"):
            left_values, right_values = manifests[left][field], manifests[right][field]
            if not isinstance(left_values, list) or not isinstance(right_values, list):
                raise TypeError("Split identities must be lists")
            if set(left_values) & set(right_values):
                raise ValueError(f"Split leakage in {field}")
    runtime = fixture_root().parent / ".runtime"
    runtime.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=runtime, prefix="evaluation-") as temporary:
        root = Path(temporary)
        corpus = root / "training.txt"
        corpus.write_text(
            "\n".join(sorted({source.text for case in splits["train"] for source in case.sources})),
            encoding="utf-8",
        )
        nlp = NarrativeEngine(p, corpus=corpus, auto_cached_model=False)
        repo = EvidenceRepository(root / "evidence", p)
        try:
            calibration = evaluate(splits["calibration"], nlp, repo)
            freeze = {
                "frozen_at_utc": datetime.now(UTC).isoformat(),
                "parameter_set_id": p.parameter_set_id,
                "parameters": p.model_dump(mode="json"),
                "embedding_mode": nlp.mode.value,
                "embedding_revision": nlp.revision,
                "training_corpus_sha256": nlp.corpus_hash,
                "splits": manifests,
                "calibration": metrics(calibration),
                "threshold_changes": [],
                "policy": "No tuning against test; one test execution.",
            }
            output.with_suffix(".freeze.json").write_bytes(canonical_bytes(freeze))
            test_rows = evaluate(splits["test"], nlp, repo)
            with repo.transaction() as db:
                media_id, _ = repo.put_artifact(
                    db,
                    media_bytes("spliced"),
                    "MEDIA",
                    "image/jpeg",
                    DataOrigin.SYNTHETIC_REPLAY,
                    "evaluation",
                )
            forensic = MediaEngine(repo, "evaluation").verify(media_id)
            with Image.open(fixture_root() / "evaluation" / "spliced-mask.png") as image:
                truth = np.asarray(image) > 0
            predicted_mask = np.zeros(truth.shape, dtype=bool)
            height, width = truth.shape
            for box in forensic.heatmap_regions:
                predicted_mask[
                    int(box.y * height) : int(np.ceil((box.y + box.h) * height)),
                    int(box.x * width) : int(np.ceil((box.x + box.w) * width)),
                ] = True
            union = int(np.logical_or(truth, predicted_mask).sum())
            iou = float(np.logical_and(truth, predicted_mask).sum() / union) if union else 1
            test_metrics = metrics(test_rows)
            test_f1 = test_metrics["f1"]
            if not isinstance(test_f1, (int, float)):
                raise TypeError("F1 must be numeric")
            result = {
                "version": "heldout-synthetic-v1",
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "parameter_set_id": p.parameter_set_id,
                "mode": nlp.mode.value,
                "embedding_revision": nlp.revision,
                "training_corpus_sha256": nlp.corpus_hash,
                "splits": manifests,
                "calibration": metrics(calibration),
                "test": metrics(test_rows),
                "per_language": {
                    language: metrics([row for row in test_rows if row["language"] == language])
                    for language in ("en", "hi", "hinglish")
                },
                "test_rows": test_rows,
                "ela": {
                    "iou": iou,
                    "region_count": len(forensic.heatmap_regions),
                    "mask_sha256": sha256(
                        (fixture_root() / "evaluation" / "spliced-mask.png").read_bytes()
                    ),
                    "media_sha256": sha256(media_bytes("spliced")),
                },
                "targets": {
                    "coordination_f1_min": 0.85,
                    "coordination_target_met": test_f1 >= 0.85,
                    "ela_iou_min": 0.70,
                    "ela_target_met": iou >= 0.70,
                },
                "model_mode_evaluation": {
                    "status": "UNSUPPORTED",
                    "reason": "Frozen-fallback evaluation only; no optional model F1 claimed.",
                },
                "limitations": [
                    "Small synthetic evaluation; no production accuracy "
                    "or intent/falsity inference.",
                    "Topic families, template sets, account identities and seeds are disjoint; "
                    "fallback vocabulary fits train only.",
                    "Benign coordinated mobilisation is a positive coordination observation, "
                    "but a negative alert control.",
                    "Bot indicators are heuristic; high indicators on benign volunteers "
                    "are not automation proof.",
                    "One synthetic localization mask is exploratory, "
                    "not a representative image benchmark.",
                    "Hindi/Hinglish cases are bilingual synthetic templates, "
                    "not general monolingual semantic validation.",
                ],
                "integrity": repo.verify("evaluation"),
            }
            output.write_text(
                json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            print(
                json.dumps(
                    {"test": result["test"], "ela": result["ela"], "targets": result["targets"]},
                    indent=2,
                )
            )
        finally:
            repo.close()
