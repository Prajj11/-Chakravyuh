"""Disjoint topic families, templates, identities and seeds for synthetic evaluation."""

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from app.evidence.canonical import canonical_bytes, sha256
from app.ingestion.contracts import SourceEvent
from app.schemas.models import AccountProfile, DataOrigin, InteractionType, PlatformType

Split = Literal["train", "calibration", "test"]
FAMILIES = {
    "train": ("railway", "sports", "agriculture"),
    "calibration": ("cinema", "energy", "heritage"),
    "test": ("water", "library", "school"),
}
SEEDS = {"train": (11, 12, 13), "calibration": (21, 22, 23), "test": (31, 32, 33)}
PREFIXES = {
    "train": {
        "en": "Public report on",
        "hi": "सार्वजनिक सूचना के अनुसार",
        "hinglish": "Public soochna ke mutabik",
    },
    "calibration": {
        "en": "Regional bulletin concerning",
        "hi": "क्षेत्रीय संदेश के विषय में",
        "hinglish": "Kshetriya sandesh ke vishay mein",
    },
    "test": {
        "en": "Local observations regarding",
        "hi": "स्थानीय अवलोकन के संदर्भ में",
        "hinglish": "Sthaniya avlokan ke sandarbh mein",
    },
}
DETAILS = {
    "train": (
        "All scheduled services are postponed pending inspection.",
        "Volunteers gather donated meals at the announced venue.",
        "Vehicle logs mention a broken fixture; route registers show repairs; "
        "soil samples record rain; public access paths were inspected; "
        "a notice records routine opening times.",
    ),
    "calibration": (
        "An administrative announcement changes the opening schedule.",
        "Publicly scheduled teams prepare community assistance at the meeting point.",
        "An exhibit has new lighting; a meter was replaced yesterday; "
        "restoration plans mention masonry; a caretaker found a lost bag; "
        "access was delayed by a public event.",
    ),
    "test": (
        "The maintenance notice asks residents to attend a public briefing.",
        "Neighbourhood volunteers organize supplies for a publicly announced service day.",
        "A valve inspection records low pressure; a librarian catalogues donated novels; "
        "a driver checks a route timetable; a parent asks about morning pickup; "
        "a visitor notes the accessible entrance.",
    ),
}


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    split: Split
    family: str
    template_id: str
    seed: int
    language: str
    category: str
    expected_coordination: bool | None
    sources: tuple[SourceEvent, ...]


def build_split(split: Split) -> tuple[EvaluationCase, ...]:
    cases = []
    for family, seed in zip(FAMILIES[split], SEEDS[split], strict=True):
        for language in ("en", "hi", "hinglish"):
            for category in (
                "repeated_copy",
                "benign_mobilisation",
                "ordinary_viral",
                "unique_observations",
                "insufficient_history",
            ):
                key = f"{split}:{family}:{language}:{category}:{seed}"
                case_id = sha256(key.encode())[:24]
                rng = random.Random(seed)
                authors = 20 if category == "ordinary_viral" else 5
                waves = 1 if category in {"ordinary_viral", "insufficient_history"} else 3
                sources = []
                for author in range(authors):
                    actor = sha256(f"{case_id}:{author}".encode())[:20]
                    profile = AccountProfile(
                        account_id=f"simulator:{actor}",
                        handle=f"@observer_{actor}_{author:06d}",
                        created_at=None
                        if author % 4 == 0
                        else datetime(2026, 9, 1, tzinfo=UTC) + timedelta(hours=author),
                    )
                    for wave in range(waves):
                        detail = DETAILS[split][1 if category == "benign_mobilisation" else 0]
                        if category == "unique_observations":
                            snippets = DETAILS[split][2].split("; ")
                            detail = (
                                f"{snippets[(author + wave) % len(snippets)]} "
                                f"Location marker {author}, observation {wave}."
                            )
                        if category == "repeated_copy":
                            detail += " panic now"
                        text = f"{PREFIXES[split][language]} {family}: {detail}"
                        if language == "hi":
                            text += " कृपया जानकारी की जाँच करें।"
                        if language == "hinglish":
                            text += " Kripya jaankari ki jaanch karein."
                        sources.append(
                            SourceEvent(
                                source_event_key=f"{actor}-{wave}",
                                platform=PlatformType.SIMULATOR,
                                data_origin=DataOrigin.SYNTHETIC_REPLAY,
                                collector_id="evaluation-replay-v1",
                                collector_scope=case_id,
                                timestamp_utc=datetime(2026, 10, 1, tzinfo=UTC)
                                + timedelta(seconds=wave * 180 + author * 2 + rng.randint(0, 1)),
                                account=profile,
                                text=text,
                                language=language,
                                interaction_type=InteractionType.REPOST
                                if category
                                in {"repeated_copy", "benign_mobilisation", "ordinary_viral"}
                                and author
                                else InteractionType.ORIGINAL_POST,
                            )
                        )
                expected = (
                    None
                    if category == "insufficient_history"
                    else category in {"repeated_copy", "benign_mobilisation"}
                )
                cases.append(
                    EvaluationCase(
                        case_id,
                        split,
                        family,
                        f"{split}-{language}-{category}",
                        seed,
                        language,
                        category,
                        expected,
                        tuple(
                            sorted(
                                sources,
                                key=lambda source: (source.timestamp_utc, source.source_event_key),
                            )
                        ),
                    )
                )
    return tuple(cases)


def split_manifest(cases: tuple[EvaluationCase, ...]) -> dict[str, object]:
    return {
        "families": sorted({case.family for case in cases}),
        "templates": sorted({case.template_id for case in cases}),
        "seeds": sorted({case.seed for case in cases}),
        "case_count": len(cases),
        "account_ids": sorted(
            {source.account.account_id for case in cases for source in case.sources}
        ),
        "dataset_sha256": sha256(
            canonical_bytes([source for case in cases for source in case.sources])
        ),
    }
