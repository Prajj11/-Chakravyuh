"""Collect an auditable, unlabelled HN corpus using organizer-supplied search terms.

This staging dataset is independent of the dashboard's supported platform contract.
Run from backend: python -m app.ingestion.public_dataset --help
"""

import argparse
import hashlib
import json
import re
import sqlite3
import time
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[3]
ENDPOINT = "https://hn.algolia.com/api/v1/search_by_date"
INPUTS = ("Hashtags .txt", "hashtags2.txt")
VERSION = "organizer-hn-v1"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def terms_from_text(text: str) -> list[str]:
    quoted = re.findall(r'"([^"\r\n]+)"', text)
    remainder = re.sub(r'"[^"\r\n]+"', " ", text)
    hashtags = re.findall(r"#[^\s(),]+", remainder)
    return list(dict.fromkeys(normalized(term) for term in quoted + hashtags))


def keyword_manifest(folder: Path) -> dict[str, Any]:
    terms: dict[str, list[str]] = {}
    files = []
    for name in INPUTS:
        raw = (folder / name).read_bytes()
        files.append({"file": name, "bytes": len(raw), "sha256": digest(raw)})
        for term in terms_from_text(raw.decode("utf-8-sig")):
            terms.setdefault(term, []).append(name)
    return {"version": VERSION, "files": files, "terms": terms}


class PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "br", "pre", "li"}:
            self.parts.append("\n")


def plain_text(value: str | None) -> str:
    parser = PlainText()
    parser.feed(value or "")
    return "".join(parser.parts).strip()


def matches(text: str, terms: list[str]) -> list[str]:
    text = normalized(text)
    return [
        term
        for term in terms
        if term in text and re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text)
    ]


def normalize_hit(hit: dict[str, Any], terms: list[str]) -> dict[str, Any] | None:
    # Match the item's own text only, never author names or its parent story's title.
    text = "\n".join(
        part
        for part in (
            plain_text(hit.get("title")),
            plain_text(hit.get("story_text")),
            plain_text(hit.get("comment_text")),
        )
        if part
    )
    found = matches(text, terms)
    identifier = str(hit.get("objectID", ""))
    timestamp = hit.get("created_at")
    tags = hit.get("_tags", [])
    kind = "comment" if "comment" in tags else "story" if "story" in tags else None
    if not found or not identifier.isdigit() or not timestamp or kind is None:
        return None
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return None
    return {
        "record_id": f"hacker_news:{identifier}",
        "platform": "hacker_news",
        "data_origin": "PUBLIC_OSINT",
        "source_id": identifier,
        "source_url": f"https://news.ycombinator.com/item?id={identifier}",
        "created_at": timestamp,
        "author": hit.get("author"),
        "record_type": kind,
        "text": text,
        "text_sha256": digest(normalized(text).encode()),
        "parent_source_id": hit.get("parent_id"),
        "thread_source_id": hit.get("story_id"),
        "linked_url": hit.get("url"),
        "points": hit.get("points"),
        "comment_count": hit.get("num_comments"),
        "matched_terms": found,
        "language": None,
        "author_location": None,
        "media_bytes_available": False,
        "disinformation_label": None,
        "coordination_label": None,
        "bot_label": None,
    }


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None


def fetch(params: dict[str, Any]) -> tuple[bytes, str]:
    url = ENDPOINT + "?" + urlencode(params)
    request = Request(
        url, headers={"User-Agent": "Chakravyuh-Research/0.1", "Accept": "application/json"}
    )
    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        raw = response.read(12_000_001)
        if len(raw) > 12_000_000:
            raise ValueError("API response exceeded 12 MB")
        return raw, url


def open_store(folder: Path, manifest: dict[str, Any], since: int) -> sqlite3.Connection:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "raw").mkdir(exist_ok=True)
    db = sqlite3.connect(folder / "collection.sqlite3")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS jobs (
          id INTEGER PRIMARY KEY, term TEXT, lower_bound INTEGER, upper_bound INTEGER,
          page INTEGER DEFAULT 0, done INTEGER DEFAULT 0,
          UNIQUE(term, lower_bound, upper_bound));
        CREATE TABLE IF NOT EXISTS captures (
          id INTEGER PRIMARY KEY, sha256 TEXT, url TEXT, captured_at TEXT, job_id INTEGER,
          page INTEGER, returned INTEGER, accepted INTEGER);
        CREATE TABLE IF NOT EXISTS posts (id TEXT PRIMARY KEY, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS observations (
          post_id TEXT, capture_id INTEGER, pointer TEXT,
          PRIMARY KEY(post_id, capture_id));
    """)
    signature = digest(json.dumps(manifest, sort_keys=True).encode())
    previous = db.execute("SELECT value FROM metadata WHERE key='input_hash'").fetchone()
    if previous and previous[0] != signature:
        raise ValueError("Keyword inputs changed; use a new output folder")
    if not previous:
        until = int(datetime.now(UTC).timestamp())
        with db:
            db.executemany(
                "INSERT INTO metadata VALUES (?,?)",
                [("input_hash", signature), ("since", str(since)), ("until", str(until))],
            )
            # Narrow topics first; high-volume queries split into smaller time intervals.
            terms = sorted(manifest["terms"], key=lambda term: (-len(term), term))
            db.executemany(
                "INSERT INTO jobs(term,lower_bound,upper_bound) VALUES (?,?,?)",
                [(term, since, until) for term in terms],
            )
        write_json(folder / "keywords.json", manifest)
    elif int(db.execute("SELECT value FROM metadata WHERE key='since'").fetchone()[0]) != since:
        raise ValueError("Start date changed; use a new output folder")
    return db


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ingest_page(
    db: sqlite3.Connection,
    folder: Path,
    job: tuple[Any, ...],
    raw: bytes,
    url: str,
    terms: list[str],
) -> None:
    job_id, term, lower, upper, page = job
    payload = json.loads(raw)
    hits = payload.get("hits")
    if not isinstance(hits, list) or not isinstance(payload.get("nbHits"), int):
        raise ValueError("Unexpected search response schema")
    raw_hash = digest(raw)
    path = folder / "raw" / (raw_hash + ".json")
    if not path.exists():
        path.write_bytes(raw)
    elif digest(path.read_bytes()) != raw_hash:
        raise ValueError("Raw response integrity failure")
    captured = datetime.now(UTC).isoformat()
    with db:
        cursor = db.execute(
            "INSERT INTO captures VALUES (NULL,?,?,?,?,?,?,0)",
            (raw_hash, url, captured, job_id, page, len(hits)),
        )
        capture_id = cursor.lastrowid
        accepted = 0
        for index, hit in enumerate(hits):
            row = normalize_hit(hit, terms)
            if row is None:
                continue
            row.update(
                {
                    "first_collected_at": captured,
                    "raw_response_sha256": raw_hash,
                    "raw_pointer": f"/hits/{index}",
                }
            )
            db.execute(
                "INSERT OR IGNORE INTO posts VALUES (?,?)",
                (row["record_id"], json.dumps(row, ensure_ascii=False)),
            )
            db.execute(
                "INSERT OR IGNORE INTO observations VALUES (?,?,?)",
                (row["record_id"], capture_id, f"/hits/{index}"),
            )
            accepted += 1
        db.execute("UPDATE captures SET accepted=? WHERE id=?", (accepted, capture_id))
        # The public search API limits accessible results. Partition time instead of
        # silently reporting a capped query as complete. Bounds never overlap.
        if page == 0 and payload["nbHits"] > 1000 and upper - lower > 1:
            middle = (lower + upper) // 2
            db.executemany(
                "INSERT OR IGNORE INTO jobs(term,lower_bound,upper_bound) VALUES (?,?,?)",
                [(term, lower, middle), (term, middle, upper)],
            )
            db.execute("UPDATE jobs SET done=1 WHERE id=?", (job_id,))
        elif hits and page + 1 < payload.get("nbPages", 0):
            db.execute("UPDATE jobs SET page=page+1 WHERE id=?", (job_id,))
        else:
            db.execute("UPDATE jobs SET done=1 WHERE id=?", (job_id,))


def export(db: sqlite3.Connection, folder: Path, status: str, target: int) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    types: Counter[str] = Counter()
    authors: set[str] = set()
    dates = []
    content_hashes: set[str] = set()
    count = 0
    bihar_count = 0
    with (
        (folder / "posts.jsonl").open("w", encoding="utf-8", newline="\n") as stream,
        (folder / "posts_bihar_mentions.jsonl").open("w", encoding="utf-8", newline="\n") as subset,
    ):
        for (body,) in db.execute("SELECT body FROM posts ORDER BY id"):
            stream.write(body + "\n")
            row = json.loads(body)
            if matches(row["text"], ["bihar", "बिहार"]):
                subset.write(body + "\n")
                bihar_count += 1
            count += 1
            counts.update(row["matched_terms"])
            types.update([row["record_type"]])
            if row["author"]:
                authors.add(row["author"])
            dates.append(row["created_at"])
            content_hashes.add(row["text_sha256"])
    captures = [
        dict(
            zip(
                (
                    "capture_id",
                    "sha256",
                    "url",
                    "collected_at",
                    "job_id",
                    "page",
                    "returned",
                    "accepted",
                ),
                row,
                strict=True,
            )
        )
        for row in db.execute("SELECT * FROM captures ORDER BY id")
    ]
    write_json(folder / "captures.json", captures)
    summary = {
        "version": VERSION,
        "status": status,
        "target_posts": target,
        "posts": count,
        "authors": len(authors),
        "record_types": dict(types),
        "distinct_texts": len(content_hashes),
        "bihar_mention_posts": bihar_count,
        "bihar_subset_sha256": digest((folder / "posts_bihar_mentions.jsonl").read_bytes()),
        "matching_terms": dict(counts.most_common()),
        "earliest_post": min(dates) if dates else None,
        "latest_post": max(dates) if dates else None,
        "requests": len(captures),
        "pending_jobs": db.execute("SELECT count(*) FROM jobs WHERE done=0").fetchone()[0],
        "posts_sha256": digest((folder / "posts.jsonl").read_bytes()),
        "labels_available": False,
        "dashboard_imported": False,
        "limitations": [
            "Single-platform convenience sample from Hacker News search index",
            "Keyword relevance is not a disinformation or coordination label",
            "Generic cybercrime terms need not concern Bihar",
            "Author geography, calibrated bot labels and media bytes unavailable",
            "Reply links may reference records outside this keyword sample",
            "Distinct posts with identical text retained for coordination analysis",
            "Collection stops at a page boundary; total can exceed target by 99",
        ],
    }
    write_json(folder / "summary.json", summary)
    return summary


def collect(
    folder: Path, manifest: dict[str, Any], since: int, target: int, max_requests: int, delay: float
) -> dict[str, Any]:
    db = open_store(folder, manifest, since)
    terms = list(manifest["terms"])
    status = "REQUEST_BUDGET_REACHED"
    try:
        for _ in range(max_requests):
            count = db.execute("SELECT count(*) FROM posts").fetchone()[0]
            if count >= target:
                status = "TARGET_REACHED"
                break
            job = db.execute(
                "SELECT id,term,lower_bound,upper_bound,page FROM jobs "
                "WHERE done=0 ORDER BY page,id LIMIT 1"
            ).fetchone()
            if job is None:
                status = "QUERIES_EXHAUSTED"
                break
            params = {
                "query": '"' + job[1] + '"',
                "page": job[4],
                "hitsPerPage": 100,
                "typoTolerance": "false",
                "queryType": "prefixNone",
                "restrictSearchableAttributes": "title,story_text,comment_text",
                "numericFilters": f"created_at_i>={job[2]},created_at_i<{job[3]}",
            }
            try:
                raw, url = fetch(params)
                ingest_page(db, folder, job, raw, url, terms)
            except HTTPError as error:
                status = f"PAUSED_HTTP_{error.code}"
                write_json(
                    folder / "last_error.json",
                    {
                        "status": status,
                        "retry_after": error.headers.get("Retry-After"),
                        "job_id": job[0],
                        "time": datetime.now(UTC).isoformat(),
                    },
                )
                break
            except (URLError, TimeoutError, ValueError) as error:
                status = "PAUSED_NETWORK_OR_RESPONSE_ERROR"
                write_json(
                    folder / "last_error.json",
                    {"status": status, "error_type": type(error).__name__, "job_id": job[0]},
                )
                break
            if _ % 10 == 0:
                print(
                    json.dumps(
                        {"requests_this_run": _ + 1, "posts_before_page": count, "term": job[1]},
                        ensure_ascii=True,
                    ),
                    flush=True,
                )
            time.sleep(delay)
    except KeyboardInterrupt:
        status = "PAUSED_BY_USER"
    finally:
        if db.execute("SELECT count(*) FROM posts").fetchone()[0] >= target:
            status = "TARGET_REACHED"
        summary = export(db, folder, status, target)
        db.close()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=ROOT / "datasets")
    parser.add_argument("--output", type=Path, default=ROOT / "datasets" / "public_hn")
    parser.add_argument("--target", type=int, default=10_000)
    parser.add_argument("--max-requests", type=int, default=1000)
    parser.add_argument("--since", default="2020-01-01")
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.target < 1 or args.max_requests < 1 or args.delay < 0.5:
        parser.error("Positive target/request budget and delay >= 0.5 seconds required")
    manifest = keyword_manifest(args.inputs)
    if args.verify:
        print(json.dumps(verify(args.output, manifest), indent=2))
    elif args.plan_only:
        args.output.mkdir(parents=True, exist_ok=True)
        write_json(args.output / "keywords.json", manifest)
        print(json.dumps({"terms": len(manifest["terms"]), "files": manifest["files"]}))
    else:
        since = int(datetime.fromisoformat(args.since).replace(tzinfo=UTC).timestamp())
        result = collect(args.output, manifest, since, args.target, args.max_requests, args.delay)
        print(json.dumps(result, ensure_ascii=True, indent=2))


def verify(folder: Path, manifest: dict[str, Any]) -> dict[str, int]:
    """Recompute every exported record from its retained source response."""
    stored_manifest = json.loads((folder / "keywords.json").read_text(encoding="utf-8"))
    if stored_manifest != manifest:
        raise ValueError("Organizer input manifest does not match current files")
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    exported = (folder / "posts.jsonl").read_bytes()
    if digest(exported) != summary["posts_sha256"]:
        raise ValueError("Export checksum mismatch")
    captures = json.loads((folder / "captures.json").read_text(encoding="utf-8"))
    capture_hashes = {capture["sha256"] for capture in captures}
    payloads = {}
    for raw_hash in capture_hashes:
        raw = (folder / "raw" / (raw_hash + ".json")).read_bytes()
        if digest(raw) != raw_hash:
            raise ValueError("Raw response checksum mismatch")
        payloads[raw_hash] = json.loads(raw)
    ids: set[str] = set()
    for line in exported.decode("utf-8").splitlines():
        row = json.loads(line)
        if row["record_id"] in ids:
            raise ValueError("Duplicate post ID in export")
        ids.add(row["record_id"])
        raw_hash = row["raw_response_sha256"]
        if raw_hash not in capture_hashes:
            raise ValueError("Record references unregistered capture")
        index = int(row["raw_pointer"].removeprefix("/hits/"))
        expected = normalize_hit(payloads[raw_hash]["hits"][index], list(manifest["terms"]))
        if expected is None or any(row.get(key) != value for key, value in expected.items()):
            raise ValueError("Record differs from original source normalization")
    if len(ids) != summary["posts"]:
        raise ValueError("Record count mismatch")
    subset = (folder / "posts_bihar_mentions.jsonl").read_bytes()
    if digest(subset) != summary["bihar_subset_sha256"]:
        raise ValueError("Bihar subset checksum mismatch")
    expected_subset = [
        line
        for line in exported.decode("utf-8").splitlines()
        if matches(json.loads(line)["text"], ["bihar", "बिहार"])
    ]
    if subset.decode("utf-8").splitlines() != expected_subset:
        raise ValueError("Bihar subset membership mismatch")
    if len(expected_subset) != summary["bihar_mention_posts"]:
        raise ValueError("Bihar subset count mismatch")
    return {"verified_posts": len(ids), "verified_raw_responses": len(capture_hashes)}


if __name__ == "__main__":
    main()
