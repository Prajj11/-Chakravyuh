import json
from datetime import UTC, datetime

import pytest

from app.ingestion.live import Feed, Monitor, fetch, normalize
from app.jobs.worker import Worker
from app.pipeline import Pipeline
from app.repositories.evidence import EvidenceRepository
from app.repositories.state import StateRepository


def test_public_capture_analysis_and_restart_dedup(repository: EvidenceRepository) -> None:
    feed = Feed(id="test", platform="hacker_news", query="flood")
    payload = {
        "hits": [
            {
                "objectID": "123",
                "author": "observer",
                "title": "Flood warning in Patna",
                "created_at_i": int(datetime.now(UTC).timestamp()),
            }
        ]
    }
    raw = json.dumps(payload).encode()
    rows = normalize(feed, payload)
    worker = Worker(Pipeline(StateRepository(repository)))
    monitor = Monitor(worker, [feed])
    assert monitor.accept(feed, [(raw, rows)])[0] == 1
    assert worker.state.list_campaigns()[0].data_origin == "PUBLIC_OSINT"
    event = repository.search_events("", "local")[0]
    captured, _, _ = repository.artifact(event.raw_payload_ref, "local")
    assert captured == raw
    assert event.account.account_id == "hacker_news:observer"
    assert event.geospatial.source_lat is None
    assert Monitor(worker, [feed]).accept(feed, [(raw, rows)])[0] == 0
    edited = rows[0][0].model_copy(update={"text": "An edited post is not a second post"})
    assert monitor.accept(feed, [(raw, [(edited, rows[0][1])])])[0] == 0
    assert repository.event_count("local") == 1
    repository.verify("local")
    worker.executor.shutdown()


def test_credentials_required_before_network() -> None:
    with pytest.raises(ValueError, match="credential"):
        fetch(Feed(id="yt", platform="youtube", query="video"))


def test_youtube_does_not_merge_display_names() -> None:
    feed = Feed(id="yt", platform="youtube", query="video")
    payload = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "id": "comment-1",
                        "snippet": {
                            "authorDisplayName": "same name",
                            "authorChannelId": {"value": "channel-1"},
                            "textDisplay": "example",
                            "publishedAt": "2026-10-20T01:00:00Z",
                        },
                    }
                }
            }
        ]
    }
    event, pointer = normalize(feed, payload)[0]
    assert event.account.account_id == "youtube:channel-1"
    assert pointer == "/items/0/snippet/topLevelComment"
    assert event.interaction_type == "reply"


def test_deleted_accounts_are_not_a_shared_actor() -> None:
    feed = Feed(id="reddit", platform="reddit", query="news")
    payload = {
        "data": {
            "children": [
                {
                    "data": {
                        "name": "t3_x",
                        "author": "[deleted]",
                        "title": "news",
                        "created_utc": 1_700_000_000,
                        "permalink": "/r/news/x",
                    }
                }
            ]
        }
    }
    assert normalize(feed, payload) == []


def test_x_retains_direct_reply_actor() -> None:
    feed = Feed(id="x", platform="x_twitter", query="weather")
    payload = {
        "data": [
            {
                "id": "123",
                "author_id": "42",
                "text": "reply",
                "in_reply_to_user_id": "43",
                "created_at": "2026-10-20T01:00:00Z",
            }
        ]
    }
    event, _ = normalize(feed, payload)[0]
    assert event.target_account_id == "x_twitter:43"
    assert event.interaction_type == "reply"
