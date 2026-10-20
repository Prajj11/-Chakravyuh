"""Exact bytes, 64-bit DCT pHash and Q90 ELA; no inferred deepfake probabilities."""

from io import BytesIO
from pathlib import Path
from typing import Literal

import cv2
import imagehash
import numpy as np
from PIL import Image, UnidentifiedImageError

from app.evidence.canonical import sha256
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import (
    AnalysisStatus,
    ComputationMode,
    DataOrigin,
    ForensicMediaReport,
    HeatmapRegion,
)


class MediaEngine:
    def __init__(
        self,
        repository: EvidenceRepository,
        scope: str = "local",
        model_dir: Path | None = None,
    ) -> None:
        self.repository = repository
        self.scope = scope
        self.p = repository.parameters
        from app.media_forensics.classifier import ImageClassifier

        self.classifier = ImageClassifier(model_dir) if model_dir else None

    def verify(
        self, artifact_id: str, *, comparison_ids: tuple[str, ...] = ()
    ) -> ForensicMediaReport:
        data, mime, kind = self.repository.artifact(artifact_id, self.scope)
        if kind != "MEDIA":
            raise ValueError("Forensic inputs must be retained media")
        with self.repository._lock:
            row = self.repository._db.execute(
                "SELECT origin FROM evidence_artifacts WHERE artifact_id=? AND scope=?",
                (artifact_id, self.scope),
            ).fetchone()
        origin = DataOrigin(row[0])
        media_type: Literal["image", "video", "audio"] = (
            "image"
            if mime.startswith("image/")
            else "video"
            if mime.startswith("video/")
            else "audio"
        )
        status = AnalysisStatus.UNSUPPORTED
        reasons = [
            "No evaluated adapter for this media type; model and manipulation scores remain null."
        ]
        phash = None
        score = None
        exif = None
        regions: list[HeatmapRegion] = []
        heatmap_ref = None
        contributions: dict[str, float] = {}
        duplicate_count = 0
        model_score = None
        if mime in {"audio/wav", "video/mp4"}:
            from app.media_forensics.av import inspect_bytes

            try:
                contributions = inspect_bytes(data, mime)
                reasons = [
                    "Bounded audio signal or sampled video-frame diagnostics were computed.",
                    "Audio/video authenticity is unsupported without an evaluated deepfake model.",
                    "Clipping, repeated frames and recompression do not establish manipulation.",
                ]
            except ValueError:
                reasons = ["Signal diagnostics unavailable for this container or resource limit."]
        if mime in {"image/jpeg", "image/png", "image/webp"}:
            try:
                with Image.open(BytesIO(data)) as image:
                    if image.width * image.height > 24_000_000:
                        raise ValueError("Image exceeds decoded pixel limit")
                    exif = bool(image.getexif())
                    rgb = image.convert("RGB")
                phash = str(imagehash.phash(rgb, hash_size=8))
                compressed = BytesIO()
                rgb.save(compressed, "JPEG", quality=self.p.ELA_JPEG_QUALITY)
                with Image.open(BytesIO(compressed.getvalue())) as recompressed:
                    difference = np.abs(
                        np.asarray(rgb, dtype=np.float64)
                        - np.asarray(recompressed.convert("RGB"), dtype=np.float64)
                    ).mean(axis=2)
                p50, p95 = (float(value) for value in np.percentile(difference, [50, 95]))
                score = 100 * min(max((p95 - p50) / (self.p.ELA_SCORE_SCALE * max(p50, 1)), 0), 1)
                contributions = {"unamplified_p50": p50, "unamplified_p95": p95}
                mask = (difference >= max(self.p.ELA_REGION_THRESHOLD, p95)).astype(np.uint8)
                count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
                boxes = [
                    (
                        int(stats[i, 0]),
                        int(stats[i, 1]),
                        int(stats[i, 0] + stats[i, 2]),
                        int(stats[i, 1] + stats[i, 3]),
                    )
                    for i in range(1, count)
                    if stats[i, 4] >= self.p.ELA_MIN_COMPONENT_PIXELS
                ]
                boxes = merge_boxes(boxes)
                width, height = rgb.size
                regions = [
                    HeatmapRegion(
                        x=x / width,
                        y=y / height,
                        w=(right - x) / width,
                        h=(bottom - y) / height,
                        intensity=float(np.clip(difference[y:bottom, x:right].mean() / 255, 0, 1)),
                        label="ELA compression anomaly (indicator)",
                    )
                    for x, y, right, bottom in boxes
                ]
                heatmap = Image.fromarray(
                    np.minimum(255, self.p.ELA_DISPLAY_SCALE * difference).astype(np.uint8)
                )
                buffer = BytesIO()
                heatmap.save(buffer, "PNG")
                with self.repository.transaction() as db:
                    heatmap_ref, _ = self.repository.put_artifact(
                        db, buffer.getvalue(), "ANALYSIS", "image/png", origin, self.scope
                    )
                for other_id in sorted(set(comparison_ids) - {artifact_id}):
                    other_data, other_mime, other_kind = self.repository.artifact(
                        other_id, self.scope
                    )
                    with self.repository._lock:
                        other_origin = self.repository._db.execute(
                            "SELECT origin FROM evidence_artifacts WHERE artifact_id=?", (other_id,)
                        ).fetchone()[0]
                    if other_origin != origin.value:
                        raise ValueError("Related-media comparisons cannot cross origins")
                    if other_kind == "MEDIA" and other_mime in {
                        "image/jpeg",
                        "image/png",
                        "image/webp",
                    }:
                        try:
                            with Image.open(BytesIO(other_data)) as other:
                                other_hash = imagehash.phash(other.convert("RGB"), hash_size=8)
                            duplicate_count += (
                                int(str(other_hash), 16) ^ int(phash, 16)
                            ).bit_count() <= self.p.PHASH_MAX_DISTANCE
                        except (UnidentifiedImageError, OSError, ValueError):
                            # A damaged candidate remains unavailable, never a related match.
                            continue
                status = AnalysisStatus.AVAILABLE
                reasons = [
                    "Q90 RGB mean-difference ELA and 64-bit DCT pHash "
                    "were computed from retained bytes.",
                    "ELA is a compression anomaly indicator, "
                    "not proof of manipulation or a deepfake probability.",
                    "EXIF absence is not proof of stripping; C2PA has not been checked.",
                ]
                if self.classifier:
                    model_score = self.classifier.score(rgb)
                    reasons.append(
                        f"Local {self.classifier.task} classifier output is an uncalibrated "
                        "model score; it does not establish authenticity or factual truth."
                    )
            except (
                UnidentifiedImageError,
                OSError,
                ValueError,
                Image.DecompressionBombError,
            ) as exc:
                status = AnalysisStatus.FAILED
                reasons = [f"Image decoding/analysis failed: {type(exc).__name__}."]
                phash, score, exif, regions, heatmap_ref, contributions = (
                    None,
                    None,
                    None,
                    [],
                    None,
                    {},
                )
        report = ForensicMediaReport(
            computation_mode=(
                ComputationMode.MODEL_INFERENCE
                if model_score is not None
                else ComputationMode.HEURISTIC_INDICATOR
                if media_type != "image"
                else ComputationMode.COMPUTED_ELA_PHASH
            ),
            analysis_status=status,
            parameter_set_id=self.p.parameter_set_id,
            coverage_ratio=1 if status == AnalysisStatus.AVAILABLE else 0,
            missing_signals=(
                ["model_calibration", "c2pa_adapter"]
                if model_score is not None
                else ["deepfake_model", "c2pa_adapter"]
            )
            if status == AnalysisStatus.AVAILABLE
            else ["supported_decodable_media_adapter"],
            evidence_reasons=reasons,
            feature_contributions=contributions,
            media_id=artifact_id,
            media_type=media_type,
            phash=phash,
            duplicate_matches_count=int(duplicate_count),
            manipulation_indicator_score=score,
            ela_anomaly_score=score,
            deepfake_visual_score=model_score,
            model_id=self.classifier.model_id
            if self.classifier and model_score is not None
            else None,
            model_revision=self.classifier.revision
            if self.classifier and model_score is not None
            else None,
            exif_present=exif,
            heatmap_regions=regions,
            heatmap_artifact_ref=heatmap_ref,
        )
        versions = {"ela": "rgb-q90-v1", "phash": "dct64-v1"}
        if self.classifier:
            versions["image_classifier"] = self.classifier.revision
        self.repository.record_analysis(report, [sha256(data)], versions, origin, self.scope)
        return report


def merge_boxes(boxes: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    pending = sorted(boxes)
    result = []
    while pending:
        x, y, right, bottom = pending.pop(0)
        changed = True
        while changed:
            changed = False
            for index, (a, b, c, d) in enumerate(pending):
                if x < c and a < right and y < d and b < bottom:
                    x, y, right, bottom = min(x, a), min(y, b), max(right, c), max(bottom, d)
                    pending.pop(index)
                    changed = True
                    break
        result.append((x, y, right, bottom))
    return result
