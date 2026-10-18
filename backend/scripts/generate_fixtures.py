"""Rebuild deterministic source fixtures. No computed analytical scores are serialized."""

import random
from datetime import timedelta
from io import BytesIO

import h3
from PIL import Image, ImageDraw

from app.evidence.canonical import canonical_bytes, sha256
from app.ingestion.simulator import CLAIMS, SCENARIO_IDS, START, fixture_root, load_scenario
from app.schemas.models import ClaimReference, ClaimVerificationStatus


def main() -> None:
    root = fixture_root()
    for directory in ("media", "evaluation", "registries", "raw"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    rng = random.Random(142)
    original = Image.new("RGB", (640, 400))
    pixels = original.load()
    assert pixels is not None
    for y in range(400):
        for x in range(640):
            noise = rng.randint(-8, 8)
            pixels[x, y] = (
                max(0, min(255, 50 + x // 6 + noise)),
                max(0, min(255, 90 + y // 4 + noise)),
                120 + rng.randint(-6, 6),
            )
    buffer = BytesIO()
    original.save(buffer, "JPEG", quality=70)
    baseline = buffer.getvalue()
    (root / "media" / "baseline.jpg").write_bytes(baseline)
    with Image.open(BytesIO(baseline)) as image:
        spliced = image.convert("RGB")
    patch = Image.new("RGB", (180, 150))
    patch.putdata(
        [(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(180 * 150)]
    )
    spliced.paste(patch, (330, 140))
    spliced.save(root / "media" / "spliced.jpg", "JPEG", quality=98, subsampling=0)
    mask = Image.new("L", (640, 400), 0)
    ImageDraw.Draw(mask).rectangle((330, 140, 509, 289), fill=255)
    mask.save(root / "evaluation" / "spliced-mask.png")
    references = []
    for index, claim in enumerate(CLAIMS):
        relative = f"registries/advisory-{index}.txt"
        snapshot = (
            "Synthetic demo advisory. This fictional exercise supplies context only. "
            "The circulated allegation is contradicted within the fictional exercise: " + claim
        ).encode()
        (root / relative).write_bytes(snapshot)
        references.append(
            ClaimReference(
                reference_id=f"synthetic-advisory-{index}",
                claim_text=claim,
                finding=ClaimVerificationStatus.CONTRADICTED_BY_SOURCE,
                source_title=f"Synthetic demo advisory {index + 1}",
                published_at_utc=START - timedelta(days=1),
                retrieved_at_utc=START,
                snapshot_sha256=sha256(snapshot),
                snapshot_ref=relative,
                languages=["en", "hi", "hinglish"],
                applicable_region="Lucknow",
                synthetic_reference=True,
            )
        )
    (root / "registries" / "known_claims_registry.json").write_bytes(canonical_bytes(references))
    lexicon = {
        "version": "harm-lexicon-v1",
        "languages": ["en", "hi", "hinglish"],
        "phrases": [
            {
                "phrase": "block the polling station",
                "category": "ELECTORAL_MANIPULATION",
                "severity": 90,
            },
            {"phrase": "panic now", "category": "PUBLIC_PANIC", "severity": 85},
            {"phrase": "दहशत फैलाओ", "category": "PUBLIC_PANIC", "severity": 80},
            {"phrase": "matdan roko", "category": "ELECTORAL_MANIPULATION", "severity": 80},
        ],
    }
    (root / "registries" / "harm_lexicon.json").write_bytes(canonical_bytes(lexicon))
    places = [
        ("Lucknow", 26.8467, 80.9462),
        ("Delhi", 28.6139, 77.209),
        ("Mumbai", 19.076, 72.8777),
        ("Bengaluru", 12.9716, 77.5946),
        ("Kolkata", 22.5726, 88.3639),
    ]
    (root / "registries" / "gazetteer.json").write_bytes(
        canonical_bytes(
            [
                {"name": name, "lat": lat, "lon": lon, "h3_index": h3.latlng_to_cell(lat, lon, 5)}
                for name, lat, lon in places
            ]
        )
    )
    corpus = [
        f"Community {topic} observations and public discussion in {place}. {word}"
        for topic in (
            "election voting machines votes polling station",
            "relief supplies deliveries panic",
            "gardens schools transport libraries markets",
        )
        for place in ("Lucknow", "Delhi", "Mumbai", "Kolkata")
        for word in ("check local details", "verify the context", "personal observation")
    ]
    corpus += [
        "मतदान मशीन वोट बदल गए केंद्र रोकें",
        "राहत सामग्री जहरीली है जांच करो",
        "matdan machine votes badal gaye",
        "relief samaan zehreela panic karo",
    ]
    (root / "registries" / "training_corpus.txt").write_text(
        "\n".join(corpus) + "\n", encoding="utf-8"
    )
    for scenario in SCENARIO_IDS:
        (root / "raw" / f"{scenario}.jsonl").write_bytes(
            b"\n".join(canonical_bytes(source) for source in load_scenario(scenario)) + b"\n"
        )
    print("Deterministic media, raw replay and source registries generated.")


if __name__ == "__main__":
    main()
