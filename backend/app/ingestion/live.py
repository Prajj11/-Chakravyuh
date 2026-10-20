"""Opt-in public API polling. Raw responses remain evidence; secrets never enter manifests."""

import asyncio
import html
import json
import math
import os
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Literal
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import BaseModel, ConfigDict, Field

from app.evidence.canonical import canonical_bytes, sha256
from app.ingestion.contracts import SourceEvent
from app.jobs.worker import Worker
from app.reporting.delivery import AlertDelivery
from app.repositories.state import StatePartition
from app.schemas.models import (
    AccountProfile,
    CampaignAlert,
    DataOrigin,
    InteractionType,
    PlatformType,
)


class Feed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    platform: Literal["hacker_news", "youtube", "reddit", "x_twitter"]
    query: str = Field(min_length=1, max_length=512)
    interval_seconds: int = Field(default=60, ge=30, le=86400)
    max_pages: int = Field(default=2, ge=1, le=10)
    credential_env: str | None = None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        raise ValueError("HTTP redirects are disabled")


def get_json(url: str, headers: dict[str, str]) -> tuple[bytes, dict[str, Any]]:
    request = Request(url, headers={"User-Agent": "Chakravyuh/2.2 public research", **headers})
    with build_opener(NoRedirect).open(request, timeout=20) as response:
        raw = response.read(5_000_001)
    if len(raw) > 5_000_000:
        raise ValueError("Public API response exceeds 5 MB")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Expected an API object")
    return raw, value


def fetch(feed: Feed) -> list[tuple[bytes, list[tuple[SourceEvent, str]]]]:
    """Bounded newest-first polling, with explicit sample coverage rather than completeness."""
    secret = os.environ.get(feed.credential_env or "", "")
    if feed.platform != "hacker_news" and not secret:
        raise ValueError("Required API credential environment variable is missing")
    pages = []
    cursor = ""
    for page in range(feed.max_pages):
        headers = {}
        if feed.platform == "hacker_news":
            url = "https://hn.algolia.com/api/v1/search_by_date?" + urlencode(
                {"query": feed.query, "tags": "(story,comment)", "hitsPerPage": 100, "page": page}
            )
        elif feed.platform == "youtube":
            url = "https://www.googleapis.com/youtube/v3/commentThreads?" + urlencode(
                {
                    "part": "snippet",
                    "videoId": feed.query,
                    "order": "time",
                    "textFormat": "plainText",
                    "maxResults": 100,
                    "pageToken": cursor,
                }
            )
            headers = {"X-Goog-Api-Key": secret}
        elif feed.platform == "reddit":
            if not re.fullmatch(r"[A-Za-z0-9_]{1,100}", feed.query):
                raise ValueError("Reddit query must be a subreddit name")
            url = f"https://oauth.reddit.com/r/{feed.query}/new?" + urlencode(
                {"limit": 100, "after": cursor, "raw_json": 1}
            )
            headers = {"Authorization": "Bearer " + secret}
        else:
            params = {
                "query": feed.query,
                "max_results": 100,
                "tweet.fields": "created_at,author_id,lang,in_reply_to_user_id",
            }
            if cursor:
                params["next_token"] = cursor
            url = "https://api.x.com/2/tweets/search/recent?" + urlencode(params)
            headers = {"Authorization": "Bearer " + secret}
        raw, payload = get_json(url, headers)
        if "error" in payload or "errors" in payload:
            raise ValueError("Platform returned an API error")
        events = normalize(feed, payload)
        pages.append((raw, events))
        if feed.platform == "hacker_news":
            if page + 1 >= payload.get("nbPages", 0):
                break
        else:
            cursor = (
                payload.get("nextPageToken", "")
                if feed.platform == "youtube"
                else payload.get("data", {}).get("after", "")
                if feed.platform == "reddit"
                else payload.get("meta", {}).get("next_token", "")
            )
            if not cursor:
                break
    return pages


def normalize(feed: Feed, payload: dict[str, Any]) -> list[tuple[SourceEvent, str]]:
    rows = (
        payload.get("hits", [])
        if feed.platform == "hacker_news"
        else payload.get("items", [])
        if feed.platform == "youtube"
        else payload.get("data", {}).get("children", [])
        if feed.platform == "reddit"
        else payload.get("data", [])
    )
    output = []
    for index, row in enumerate(rows):
        target = None
        interaction = InteractionType.ORIGINAL_POST
        language = "und"
        if feed.platform == "hacker_news":
            key, author = str(row["objectID"]), row.get("author")
            text = row.get("comment_text") or row.get("story_text") or row.get("title") or ""
            text = html.unescape(re.sub(r"<[^>]*>", " ", text))
            stamp = datetime.fromtimestamp(row["created_at_i"], UTC)
            url = "https://news.ycombinator.com/item?id=" + key
            pointer = f"/hits/{index}"
            if row.get("comment_text"):
                interaction = InteractionType.REPLY
        elif feed.platform == "youtube":
            comment = row["snippet"]["topLevelComment"]
            body = comment["snippet"]
            key, author = comment["id"], body.get("authorChannelId", {}).get("value")
            text, stamp = body["textDisplay"], datetime.fromisoformat(body["publishedAt"])
            url = "https://www.youtube.com/watch?" + urlencode({"v": feed.query, "lc": key})
            pointer = f"/items/{index}/snippet/topLevelComment"
            interaction = InteractionType.REPLY
        elif feed.platform == "reddit":
            body = row["data"]
            key, author = body["name"], body.get("author")
            text = body.get("title", "") + "\n" + body.get("selftext", "")
            stamp = datetime.fromtimestamp(body["created_utc"], UTC)
            url = "https://www.reddit.com" + body["permalink"]
            pointer = f"/data/children/{index}/data"
        else:
            key, author = row["id"], row.get("author_id")
            text, stamp = row["text"], datetime.fromisoformat(row["created_at"])
            language = row.get("lang", "und")
            target = row.get("in_reply_to_user_id")
            interaction = InteractionType.REPLY if target else InteractionType.ORIGINAL_POST
            url, pointer = "https://x.com/i/web/status/" + key, f"/data/{index}"
        if not author or author == "[deleted]" or not text.strip():
            continue
        output.append(
            (
                SourceEvent(
                    source_event_key=key,
                    platform=PlatformType(feed.platform),
                    data_origin=DataOrigin.PUBLIC_OSINT,
                    collector_id="public-api-v1:" + feed.id,
                    collector_scope="live:" + feed.id,
                    source_url=url,
                    timestamp_utc=stamp,
                    account=AccountProfile(account_id=feed.platform + ":" + author, handle=author),
                    text=text,
                    language=language,
                    interaction_type=interaction,
                    target_account_id=feed.platform + ":" + target if target else None,
                ),
                pointer,
            )
        )
    return output


class Monitor:
    def __init__(
        self, worker: Worker, feeds: list[Feed], delivery: AlertDelivery | None = None
    ) -> None:
        if len({feed.id for feed in feeds}) != len(feeds):
            raise ValueError("Feed IDs must be unique")
        if len(feeds) > 10:
            raise ValueError("At most ten feeds can be monitored in this local deployment")
        self.worker = worker
        self.feeds = feeds
        self.delivery = delivery
        self.status: dict[str, dict[str, Any]] = {
            feed.id: {
                "platform": feed.platform,
                "state": "STARTING",
                "coverage": "BOUNDED_NEWEST_RESULTS",
                "events_seen": 0,
            }
            for feed in feeds
        }
        self.tasks: list[asyncio.Task[None]] = []
        with worker.state.evidence.transaction() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS live_seen "
                "(feed TEXT, fingerprint TEXT, PRIMARY KEY(feed,fingerprint))"
            )

    def start(self) -> None:
        self.tasks = [asyncio.create_task(self.poll(feed)) for feed in self.feeds]

    async def close(self) -> None:
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def poll(self, feed: Feed) -> None:
        failures = 0
        while True:
            retry_after = 0.0
            try:
                pages = await asyncio.to_thread(fetch, feed)
                count, alerts = await self.worker.cpu(self.accept, feed, pages)
                for alert in alerts:
                    self.worker.stream.publish(
                        "CTI_ALERT", alert, "Gated public observation warning", alert.campaign_id
                    )
                self.status[feed.id].update(
                    state="POLLING",
                    last_success=datetime.now(UTC).isoformat(),
                    events_seen=self.status[feed.id]["events_seen"] + count,
                    error=None,
                )
                failures = 0
            except Exception as exc:
                # Never expose exception text: HTTP libraries may include credential-bearing URLs.
                failures += 1
                error = type(exc).__name__
                if isinstance(exc, HTTPError):
                    error += f" ({exc.code})"
                    value = exc.headers.get("Retry-After", "")
                    try:
                        retry_after = float(value)
                    except ValueError:
                        try:
                            retry_after = (
                                parsedate_to_datetime(value) - datetime.now(UTC)
                            ).total_seconds()
                        except (ValueError, TypeError, OverflowError):
                            pass
                    if not math.isfinite(retry_after) or retry_after < 0:
                        retry_after = 0
                    exc.close()
                self.status[feed.id].update(state="BACKOFF", error=error)
            await asyncio.sleep(
                max(min(feed.interval_seconds * 2 ** min(failures, 6), 3600), retry_after)
            )

    def accept(
        self, feed: Feed, pages: list[tuple[bytes, list[tuple[SourceEvent, str]]]]
    ) -> tuple[int, list[CampaignAlert]]:
        pipeline = self.worker.pipeline
        state = self.worker.state
        partition = StatePartition(
            data_origin=DataOrigin.PUBLIC_OSINT, collector_scope="live:" + feed.id
        )
        generation = state.generation(partition)
        fingerprints = []
        alerts: list[CampaignAlert] = []
        for raw, rows in pages:
            for source, pointer in rows:
                # Preserve first-seen content; changed API counters/edits are not new posts.
                fingerprint = sha256(
                    canonical_bytes([source.collector_id, source.source_event_key])
                )
                if fingerprint in fingerprints:
                    continue
                with state.evidence.transaction() as db:
                    if db.execute(
                        "SELECT 1 FROM live_seen WHERE feed=? AND fingerprint=?",
                        (feed.id, fingerprint),
                    ).fetchone():
                        continue
                with state.mutation(partition, generation):
                    event = pipeline.ingestor.ingest(
                        source, scope=state.scope, raw_bytes=raw, source_pointer=pointer
                    )
                    state.record_account(partition, generation, event.event_id)
                fingerprints.append(fingerprint)
        if fingerprints:
            _, alerts = pipeline.refresh(partition, generation)
            if self.delivery:
                for alert in alerts:
                    watermark = pipeline.alerts[alert.campaign_id].watermark
                    if watermark is not None:
                        self.delivery.enqueue(alert, watermark.isoformat())
            with state.evidence.transaction() as db:
                db.executemany(
                    "INSERT OR IGNORE INTO live_seen VALUES (?,?)",
                    [(feed.id, value) for value in fingerprints],
                )
        return len(fingerprints), alerts
