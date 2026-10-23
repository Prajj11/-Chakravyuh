import json
from datetime import UTC, datetime

import pytest

from app.ingestion import live
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


@pytest.mark.parametrize("query", ["   ", '""', '"  "'])
def test_blank_query_cannot_collect_everything(query: str) -> None:
    with pytest.raises(ValueError, match="nonempty"):
        Feed(id="blank", platform="hacker_news", query=query)


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


def test_hn_requires_own_text_and_retains_title_and_pointer() -> None:
    feed = Feed(id="bihar", platform="hacker_news", query="Bihar")
    base = {"author": "reader", "created_at_i": 1_700_000_000}
    payload = {
        "hits": [
            {**base, "objectID": "1", "title": "Bihari cuisine"},
            {**base, "objectID": "2", "story_title": "Bihar", "comment_text": "unrelated"},
            {**base, "objectID": "3", "title": "Bihar news", "story_text": "Full story"},
            {**base, "objectID": "4", "title": "Bihar", "created_at_i": "invalid"},
            {**base, "objectID": "5", "comment_text": "<p>Bihar &amp; floods</p>"},
        ]
    }
    rows = normalize(feed, payload)
    assert [row[0].source_event_key for row in rows] == ["3", "5"]
    assert rows[0][0].text == "Bihar news\nFull story"
    assert rows[1][1] == "/hits/4"


def test_repeated_page_token_stops_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setenv("TEST_REDDIT_TOKEN", "test-only")

    def response(url: str, headers: dict[str, str]) -> tuple[bytes, dict]:
        calls.append(url)
        return b"{}", {"data": {"children": [], "after": "same-token"}}

    monkeypatch.setattr(live, "get_json", response)
    fetch(
        Feed(
            id="r",
            platform="reddit",
            query="news",
            max_pages=10,
            credential_env="TEST_REDDIT_TOKEN",
        )
    )
    assert len(calls) == 2


def test_hn_search_disables_fuzzy_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    from urllib.parse import parse_qs, urlsplit

    def response(url: str, headers: dict[str, str]) -> tuple[bytes, dict]:
        params = parse_qs(urlsplit(url).query)
        assert params["typoTolerance"] == ["false"]
        assert params["queryType"] == ["prefixNone"]
        assert params["query"] == ['"Bihar"']
        assert params["restrictSearchableAttributes"] == ["title,story_text,comment_text"]
        return b"{}", {"hits": [], "nbPages": 0}

    monkeypatch.setattr(live, "get_json", response)
    assert fetch(Feed(id="bihar", platform="hacker_news", query="Bihar")) == [(b"{}", [])]


def test_refresh_failure_reuses_first_capture(
    repository: EvidenceRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    feed = Feed(id="recovery", platform="hacker_news", query="flood")
    payload = {
        "hits": [
            {
                "objectID": "123",
                "author": "observer",
                "title": "flood",
                "created_at_i": int(datetime.now(UTC).timestamp()),
            }
        ]
    }
    worker = Worker(Pipeline(StateRepository(repository)))
    monitor = Monitor(worker, [feed])
    original_refresh = worker.pipeline.refresh

    def fail(*args: object) -> None:
        raise RuntimeError("refresh interrupted")

    try:
        monkeypatch.setattr(worker.pipeline, "refresh", fail)
        with pytest.raises(RuntimeError):
            monitor.accept(feed, [(json.dumps(payload).encode(), normalize(feed, payload))])
        monkeypatch.setattr(worker.pipeline, "refresh", original_refresh)
        payload["hits"][0]["points"] = 20
        assert (
            monitor.accept(feed, [(json.dumps(payload).encode(), normalize(feed, payload))])[0] == 1
        )
        assert repository.event_count("local") == 1
        repository.verify("local")
    finally:
        worker.executor.shutdown()
