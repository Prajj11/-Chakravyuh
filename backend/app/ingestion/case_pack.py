"""Generate 25 reproducible synthetic cases (7,500 raw posts), with no analytical scores."""

import argparse
import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import h3

from app.ingestion.case_catalogue import CASE_BY_ID, CASES, POSTS_PER_CASE
from app.ingestion.contracts import SourceEvent
from app.schemas.models import (
    AccountProfile,
    DataOrigin,
    GeospatialContext,
    InteractionType,
    LocationConfidence,
    MediaAttachment,
    PlatformType,
)

PACK_VERSION = "diverse-cases-v1"
START = datetime(2026, 10, 1, 8, tzinfo=UTC)
AUTHORS = 60
WAVES = 5


def generate_case(scenario_id: str, seed: int = 42) -> tuple[SourceEvent, ...]:
    case = CASE_BY_ID[scenario_id]
    index = CASES.index(case)
    rng = random.Random(f"{PACK_VERSION}:{scenario_id}:{seed}")
    start = START + timedelta(minutes=index * 3)
    missing = set(rng.sample(range(AUTHORS), 12))
    external = CASES[(index + 7) % len(CASES)]
    peaceful = case.pattern in {"organic", "mobilization"}
    events = []
    for author in range(AUTHORS):
        actor = f"{scenario_id}-{seed}-{author:03d}"
        known = author not in missing
        # Declared source and mentioned subject remain independent observations.
        origin = external if index % 3 == 0 and author % 4 != 0 else case
        gps = known and author % 5 == 0
        profile = AccountProfile(
            account_id="simulator:" + actor,
            handle=f"@demo_{index + 1:02d}_{seed}_{author:03d}",
            display_name=f"Synthetic participant {index + 1:02d}/{author:03d}",
            created_at=(
                start
                - timedelta(
                    days=rng.randint(180, 1500)
                    if peaceful
                    else rng.randint(3, 30)
                    if author < 36
                    else rng.randint(120, 900)
                )
            )
            if known
            else None,
            followers_count=rng.randint(5, 8000) if known else None,
            following_count=rng.randint(20, 4000) if known else None,
            profile_location=origin.city if known else None,
        )
        geography = GeospatialContext(
            source_lat=origin.lat if gps else None,
            source_lon=origin.lon if gps else None,
            source_region_name=origin.city if known else None,
            source_h3_index=h3.latlng_to_cell(origin.lat, origin.lon, 5) if known else None,
            source_location_confidence=(
                LocationConfidence.EXPLICIT_GPS
                if gps
                else LocationConfidence.PROFILE_DECLARED
                if known
                else LocationConfidence.UNAVAILABLE
            ),
            target_region_name=case.city,
            target_h3_index=h3.latlng_to_cell(case.lat, case.lon, 5),
        )
        for wave in range(WAVES):
            synchronized = case.pattern in {"synchronized", "mobilization"} or (
                case.pattern == "mixed" and author < 36
            )
            if author == 0:
                offset = 0
            elif synchronized:
                offset = rng.randint(3, 45)
            elif case.pattern == "staggered":
                offset = author * 12 + rng.randint(0, 8)
            else:
                offset = author * 71 + rng.randint(0, 35)
            seconds = wave * 4800 + offset
            language = ("en", "hi", "hinglish")[author % 3]
            body = (case.en, case.hi, case.hinglish)[author % 3]
            if peaceful or (case.pattern == "mixed" and author >= 36):
                context = (
                    f" Local observation from street {author + 1}, update {wave + 1}. "
                    + (
                        "Please compare dated sources before sharing.",
                        "The timing may differ between neighbourhoods.",
                        "Can anyone provide the original notice?",
                        "I have only seen part of the discussion.",
                        "A local check is still needed.",
                    )[(author + wave) % 5]
                )
                if language == "hi":
                    context = (
                        f" गली {author + 1} का अवलोकन, अपडेट {wave + 1}। "
                        "साझा करने से पहले तारीख और मूल स्रोत की जाँच करें।"
                    )
                elif language == "hinglish":
                    context = (
                        f" Gali {author + 1} ka observation, update {wave + 1}. "
                        "Share karne se pehle date aur original source check karein."
                    )
                body += context
            # Every record is visibly fictional even when removed from its JSON metadata.
            text = "[SYNTHETIC EXERCISE] " + body
            linked = author > 0 and case.pattern != "organic" and author % 4 != 0
            interaction = (
                (InteractionType.REPLY if author % 7 == 0 else InteractionType.REPOST)
                if linked
                else InteractionType.ORIGINAL_POST
            )
            attachments: tuple[MediaAttachment, ...] = ()
            if index % 4 == 0 and author % 3 == 0:
                attachments = (
                    MediaAttachment(
                        media_id="baseline" if peaceful else "spliced",
                        media_type="image",
                        collection_status="PENDING",
                    ),
                )
            events.append(
                SourceEvent(
                    source_event_key=f"{actor}-wave-{wave}",
                    platform=PlatformType.SIMULATOR,
                    data_origin=DataOrigin.SYNTHETIC_REPLAY,
                    collector_id=PACK_VERSION,
                    collector_scope=f"{PACK_VERSION}:{scenario_id}:seed-{seed}",
                    source_url=f"https://example.invalid/synthetic/{actor}/{wave}",
                    timestamp_utc=start + timedelta(seconds=seconds),
                    account=profile,
                    text=text,
                    language=language,
                    hashtags=(f"DemoCase{index + 1:02d}",),
                    urls=()
                    if case.pattern == "organic"
                    else (f"https://example.invalid/synthetic/{case.slug}/notice-{wave % 2}",),
                    media_attachments=attachments,
                    interaction_type=interaction,
                    parent_event_id=f"source:{scenario_id}-{seed}-000-wave-{wave}"
                    if linked
                    else None,
                    target_account_id=f"simulator:{scenario_id}-{seed}-000" if linked else None,
                    geospatial=geography,
                )
            )
    return tuple(sorted(events, key=lambda event: (event.timestamp_utc, event.source_event_key)))


def export_pack(root: Path, *, check: bool = False) -> None:
    output = root / "sample_data" / "case_pack"
    entries = []
    files: dict[Path, bytes] = {}
    for case in CASES:
        events = generate_case(case.scenario_id)
        payload = ("\n".join(event.model_dump_json() for event in events) + "\n").encode("utf-8")
        filename = case.scenario_id + ".jsonl"
        files[output / filename] = payload
        entries.append(
            {
                "scenario_id": case.scenario_id,
                "title": case.title,
                "city": case.city,
                "generation_pattern": case.pattern,
                "posts": len(events),
                "accounts": AUTHORS,
                "languages": ["en", "hi", "hinglish"],
                "file": filename,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "first_event_utc": events[0].timestamp_utc.isoformat(),
                "last_event_utc": events[-1].timestamp_utc.isoformat(),
            }
        )
    manifest = {
        "version": PACK_VERSION,
        "seed": 42,
        "data_origin": "SYNTHETIC_REPLAY",
        "total_cases": len(CASES),
        "total_posts": len(CASES) * POSTS_PER_CASE,
        "total_accounts": len(CASES) * AUTHORS,
        "notice": (
            "Fictional exercise data. Patterns are generator metadata, not detector outputs or "
            "evaluated labels. Media references reuse synthetic baseline/spliced JPEG fixtures; "
            "no audio/video is supplied."
        ),
        "cases": entries,
    }
    files[output / "manifest.json"] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    frontend = [
        {"id": case.scenario_id, "title": case.title, "city": case.city, "posts": POSTS_PER_CASE}
        for case in CASES
    ]
    files[root / "frontend/src/lib/scenario-catalogue.json"] = (
        json.dumps(frontend, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    for path, payload in files.items():
        if check:
            if not path.exists() or path.read_bytes() != payload:
                raise ValueError(f"Generated dataset differs: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    export_pack(Path(__file__).resolve().parents[3], check=arguments.check)
    print(
        "Verified" if arguments.check else "Generated",
        "25 cases, 7,500 posts, 1,500 accounts (seed 42).",
    )
