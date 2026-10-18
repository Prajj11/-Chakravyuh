"""Frozen lexical fallback, optional local multilingual model, clustering and indicators."""

import json
import re
import unicodedata
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import numpy as np
from numpy.typing import NDArray
from sklearn.feature_extraction.text import TfidfVectorizer

from app.config import Parameters
from app.evidence.canonical import canonical_bytes, sha256
from app.ingestion.simulator import fixture_root
from app.schemas.models import (
    AnalysisStatus,
    ClaimReference,
    ClaimVerificationAssessment,
    ComputationMode,
    DataOrigin,
    HarmAssessment,
    HarmCategory,
    NarrativeCluster,
    UnifiedSocialEvent,
)

Vector = NDArray[np.float64]
ALIASES = {
    "मतदान": "voting",
    "matdan": "voting",
    "चुनाव": "election",
    "chunav": "election",
    "लखनऊ": "lucknow",
    "लख़नऊ": "lucknow",
    "राहत": "relief",
    "rahat": "relief",
    "वोट": "votes",
}


def normalize_url(value: str) -> str:
    parts = urlsplit(value)
    query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in {"fbclid", "gclid"}
    ]
    return urlunsplit(
        (parts.scheme.casefold(), parts.netloc.casefold(), parts.path, urlencode(sorted(query)), "")
    )


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    text = re.sub(r"https?://[^\s]+", lambda match: normalize_url(match[0]), text)
    for alias, canonical in ALIASES.items():
        text = re.sub(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", canonical, text)
    return " ".join(text.split())


def unit(vector: Vector) -> Vector:
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm else vector


class LocalEmbedder(Protocol):
    def encode(
        self, sentences: list[str], *, normalize_embeddings: bool, show_progress_bar: bool
    ) -> Vector: ...


class NarrativeEngine:
    def __init__(
        self,
        parameters: Parameters,
        *,
        corpus: Path | None = None,
        cached_model: Path | None = None,
        auto_cached_model: bool = True,
    ) -> None:
        self.p = parameters
        path = corpus or fixture_root() / "registries" / "training_corpus.txt"
        training = path.read_bytes()
        self.corpus_hash = sha256(training)
        self.mode = ComputationMode.HEURISTIC_INDICATOR
        self.model_id = "frozen-word-char-tfidf"
        self.revision = "tfidf-v1:" + sha256(canonical_bytes([self.corpus_hash, ALIASES]))
        self.model: LocalEmbedder | None = None
        self.limitations = [
            "Lexical overlap is not general multilingual semantic understanding.",
            "Vocabulary is frozen on the recorded baseline corpus.",
        ]
        default_cache = fixture_root().parent / "models" / "paraphrase-multilingual-MiniLM-L12-v2"
        cached_model = cached_model or (
            default_cache if auto_cached_model and default_cache.is_dir() else None
        )
        if cached_model is not None:
            # Only a trusted configured local cache; uploads never select a checkpoint.
            try:
                if not cached_model.is_dir():
                    raise ValueError("Cached model directory is unavailable")
                from sentence_transformers import SentenceTransformer

                model = SentenceTransformer(
                    str(cached_model), device="cpu", local_files_only=True, trust_remote_code=False
                )
                warmup = np.asarray(
                    model.encode(
                        ["local model readiness"],
                        normalize_embeddings=True,
                        show_progress_bar=False,
                    ),
                    dtype=np.float64,
                )
                if warmup.shape != (1, 384) or not np.isfinite(warmup).all() or not warmup.any():
                    raise ValueError(
                        "Cached model must emit finite nonzero 384-dimensional vectors"
                    )
                files = sorted(file for file in cached_model.rglob("*") if file.is_file())
                revision = sha256(
                    canonical_bytes(
                        [
                            (str(file.relative_to(cached_model)), sha256(file.read_bytes()))
                            for file in files
                        ]
                    )
                )
            except (ImportError, OSError, ValueError, RuntimeError) as exc:
                self.limitations.append(
                    f"Cached multilingual model unavailable ({type(exc).__name__}); "
                    "frozen fallback is active."
                )
            else:
                self.model = model
                self.revision = revision
                self.model_id = "paraphrase-multilingual-MiniLM-L12-v2"
                self.mode = ComputationMode.MODEL_INFERENCE
                self.limitations = ["Local embedding similarity requires contextual human review."]
        texts = [
            normalize_text(line) for line in training.decode("utf-8").splitlines() if line.strip()
        ]
        self.word = TfidfVectorizer(ngram_range=(1, 2), lowercase=False)
        self.char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=False)
        self.word.fit(texts)
        self.char.fit(texts)
        self.cluster_reasons: dict[str, list[str]] = {}
        lexicon = json.loads(
            (fixture_root() / "registries" / "harm_lexicon.json").read_text(encoding="utf-8")
        )
        self.harm_languages = set(lexicon["languages"])
        self.harm_phrases = [
            (normalize_text(item["phrase"]), HarmCategory(item["category"]), int(item["severity"]))
            for item in lexicon["phrases"]
        ]
        self.harm_revision = lexicon["version"]

    def embed(self, texts: Sequence[str]) -> Vector:
        if not texts:
            return np.empty((0, 0), dtype=np.float64)
        normalized = [normalize_text(text) for text in texts]
        if self.model is not None:
            vectors = np.asarray(
                self.model.encode(normalized, normalize_embeddings=True, show_progress_bar=False),
                dtype=np.float64,
            )
            if vectors.shape[1] != 384:
                raise ValueError("The cached multilingual model must emit 384 dimensions")
            return vectors
        vectors = np.hstack(
            (self.word.transform(normalized).toarray(), self.char.transform(normalized).toarray())
        ).astype(np.float64)
        return np.array([unit(vector) for vector in vectors])

    def cluster(
        self, events: Sequence[UnifiedSocialEvent], *, partition_id: str
    ) -> list[NarrativeCluster]:
        if not events:
            return []
        watermark = max(event.timestamp_utc for event in events)
        active = sorted(
            {
                event.event_id: event
                for event in events
                if event.timestamp_utc > watermark - timedelta(hours=self.p.NARRATIVE_WINDOW_HOURS)
            }.values(),
            key=lambda event: (event.timestamp_utc, event.event_id),
        )
        vectors = self.embed([event.text for event in active])
        groups: dict[str, list[int]] = {}
        centroids: dict[str, Vector] = {}
        self.cluster_reasons = {}
        for index, event in enumerate(active):
            vector = vectors[index]
            candidates = [
                (float(np.dot(vector, centroid)), key)
                for key, centroid in centroids.items()
                if vector.any() and centroid.any()
            ]
            candidates.sort(key=lambda item: (-item[0], item[1]))
            if candidates and candidates[0][0] >= self.p.SEMANTIC_CLUSTER_SIMILARITY:
                campaign_id = candidates[0][1]
            else:
                campaign_id = (
                    "cmp_"
                    + sha256(canonical_bytes([partition_id, event.event_id, self.revision]))[:20]
                )
                groups[campaign_id] = []
                self.cluster_reasons[campaign_id] = [
                    "Zero vocabulary vector; no semantic assignment."
                    if not vector.any()
                    else "New narrative centroid."
                ]
            groups[campaign_id].append(index)
            centroids[campaign_id] = unit(np.mean(vectors[groups[campaign_id]], axis=0))
        return [
            NarrativeCluster(
                campaign_id=key,
                event_ids=[active[i].event_id for i in indices],
                embedding_mode=self.mode,
                embedding_model_id=self.model_id,
                embedding_revision=self.revision,
                centroid=centroids[key].tolist(),
                first_detected_utc=active[indices[0]].timestamp_utc,
                last_updated_utc=active[indices[-1]].timestamp_utc,
            )
            for key, indices in sorted(groups.items())
        ]

    def claim(
        self,
        text: str,
        origin: DataOrigin,
        timestamp: datetime,
        references: Sequence[ClaimReference],
    ) -> ClaimVerificationAssessment:
        valid = [
            reference
            for reference in references
            if (not reference.synthetic_reference or origin == DataOrigin.SYNTHETIC_REPLAY)
            and reference.published_at_utc <= timestamp
            and (reference.valid_until_utc is None or timestamp <= reference.valid_until_utc)
        ]
        candidate = None
        similarity = None
        reason = "No context-valid candidate meets retrieval threshold."
        if valid:
            vectors = self.embed([text] + [ref.claim_text for ref in valid])
            ranked = sorted(
                [
                    (float(np.clip(np.dot(vectors[0], vectors[i + 1]), 0, 1)), ref)
                    for i, ref in enumerate(valid)
                ],
                key=lambda item: (-item[0], item[1].reference_id),
            )
            matches = [item for item in ranked if item[0] >= self.p.CLAIM_CANDIDATE_SIMILARITY]
            if matches and len({item[1].finding for item in matches}) == 1:
                similarity, candidate = matches[0]
                reason = (
                    "Candidate wording retrieved; date, location, actors and media "
                    "require human review."
                )
            elif matches:
                reason = "Conflicting candidate findings; context remains unresolved."
        return ClaimVerificationAssessment(
            computation_mode=self.mode,
            analysis_status=AnalysisStatus.AVAILABLE
            if candidate
            else AnalysisStatus.INSUFFICIENT_DATA,
            parameter_set_id=self.p.parameter_set_id,
            coverage_ratio=1 if candidate else 0,
            missing_signals=[] if candidate else ["context_valid_reference"],
            evidence_reasons=[
                reason,
                f"Embedding: {self.model_id} @ {self.revision}.",
                f"Frozen baseline corpus SHA-256: {self.corpus_hash}.",
                *self.limitations,
            ],
            candidate_reference=candidate,
            similarity_to_known_claim=similarity,
        )

    def harm(self, events: Sequence[UnifiedSocialEvent]) -> HarmAssessment:
        supported = [event for event in events if event.language in self.harm_languages]
        coverage = len(supported) / len(events) if events else 0
        matched: list[tuple[int, HarmCategory, str]] = []
        per_post = []
        for event in supported:
            text = normalize_text(event.text)
            matches = [
                (severity, category, phrase)
                for phrase, category, severity in self.harm_phrases
                if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text)
            ]
            matched.extend(matches)
            per_post.append(max((match[0] for match in matches), default=0))
        available = bool(supported) and coverage >= self.p.HARM_MIN_LANGUAGE_COVERAGE
        category = (
            max(matched, key=lambda item: (item[0], item[1]))[1] if matched else HarmCategory.BENIGN
        )
        return HarmAssessment(
            computation_mode=ComputationMode.HEURISTIC_INDICATOR,
            analysis_status=AnalysisStatus.AVAILABLE
            if available
            else AnalysisStatus.INSUFFICIENT_DATA,
            parameter_set_id=self.p.parameter_set_id,
            coverage_ratio=coverage,
            missing_signals=[] if available else ["supported_language_coverage"],
            evidence_reasons=[
                f"{self.harm_revision}: exact phrase indicator; "
                "quotations/context can change meaning.",
                "Matched phrases: " + ", ".join(sorted({item[2] for item in matched})),
            ],
            category=category,
            harm_indicator_score=sum(per_post) / len(per_post) if available else None,
        )
