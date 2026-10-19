import json
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

import pytest

from app.ingestion import public_dataset
from app.ingestion.public_dataset import (
    digest,
    export,
    ingest_page,
    normalize_hit,
    open_store,
    terms_from_text,
    verify,
)


def test_keywords_and_own_text_matching() -> None:
    assert terms_from_text('"Bihar" OR "BIHAR"\n#बिहार #BiharFlood') == [
        "bihar",
        "#बिहार",
        "#biharflood",
    ]
    hit = {
        "objectID": "123",
        "created_at": "2026-01-01T00:00:00Z",
        "_tags": ["comment"],
        "comment_text": "<p>Bihari people</p>",
        "story_title": "Bihar",
        "author": "bihar",
    }
    assert normalize_hit(hit, ["bihar"]) is None
    hit["comment_text"] = "<p>Bihar &amp; floods</p>"
    row = normalize_hit(hit, ["bihar"])
    assert row is not None
    assert row["text"] == "Bihar & floods"
    assert row["disinformation_label"] is None
    assert row["author_location"] is None


def test_raw_provenance_deduplication_and_checkpoint(tmp_path: Path) -> None:
    manifest = {"terms": {"bihar": ["input.txt"]}}
    db = open_store(tmp_path, manifest, 0)
    job = db.execute("SELECT id,term,lower_bound,upper_bound,page FROM jobs").fetchone()
    raw = json.dumps(
        {
            "nbHits": 2,
            "nbPages": 2,
            "hits": [
                {
                    "objectID": "123",
                    "created_at": "2026-01-01T00:00:00Z",
                    "_tags": ["comment"],
                    "comment_text": "Bihar flood",
                    "author": "a",
                },
            ],
        }
    ).encode()
    ingest_page(db, tmp_path, job, raw, "https://hn.algolia.com/example", ["bihar"])
    ingest_page(db, tmp_path, job, raw, "https://hn.algolia.com/example", ["bihar"])
    assert db.execute("SELECT count(*) FROM posts").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM observations").fetchone()[0] == 2
    assert (tmp_path / "raw" / (digest(raw) + ".json")).read_bytes() == raw
    summary = export(db, tmp_path, "PAUSED", 10_000)
    assert summary["posts"] == 1
    assert summary["dashboard_imported"] is False
    assert verify(tmp_path, manifest)["verified_posts"] == 1
    (tmp_path / "raw" / (digest(raw) + ".json")).write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify(tmp_path, manifest)
    db.close()
    db = open_store(tmp_path, manifest, 0)
    assert db.execute("SELECT page FROM jobs").fetchone()[0] == 2
    db.close()
    with pytest.raises(ValueError, match="Keyword inputs changed"):
        open_store(tmp_path, {"terms": {"other": []}}, 0)


def test_large_result_sets_split_disjoint_time_intervals(tmp_path: Path) -> None:
    db = open_store(tmp_path, {"terms": {"phishing": []}}, 0)
    job = db.execute("SELECT id,term,lower_bound,upper_bound,page FROM jobs").fetchone()
    ingest_page(
        db,
        tmp_path,
        job,
        b'{"nbHits":1001,"nbPages":10,"hits":[]}',
        "https://hn.algolia.com/example",
        ["phishing"],
    )
    jobs = db.execute(
        "SELECT lower_bound,upper_bound FROM jobs WHERE done=0 ORDER BY id"
    ).fetchall()
    assert len(jobs) == 2
    assert jobs[0][0] == 0
    assert jobs[0][1] == jobs[1][0]
    assert jobs[1][1] == job[3]
    db.close()


def test_rate_limit_pauses_without_advancing_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def blocked(params: dict[str, object]) -> tuple[bytes, str]:
        nonlocal calls
        calls += 1
        headers = Message()
        headers["Retry-After"] = "60"
        raise HTTPError("https://hn.algolia.com/", 429, "rate limit", headers, None)

    monkeypatch.setattr(public_dataset, "fetch", blocked)
    manifest = {"terms": {"bihar": []}}
    result = public_dataset.collect(tmp_path, manifest, 0, 10000, 10, 0.5)
    assert calls == 1
    assert result["status"] == "PAUSED_HTTP_429"
    assert result["posts"] == 0
    db = open_store(tmp_path, manifest, 0)
    assert db.execute("SELECT page,done FROM jobs").fetchone() == (0, 0)
    db.close()
