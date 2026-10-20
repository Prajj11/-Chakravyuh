import json
import time
from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.ingestion.case_catalogue import CASES
from app.ingestion.case_pack import export_pack, generate_case
from app.ingestion.contracts import SourceEvent
from app.main import create_app
from app.schemas.models import ScenarioSwitchRequest


def test_generated_pack_is_reproducible_and_complete() -> None:
    root = Path(__file__).resolve().parents[2]
    export_pack(root, check=True)
    events = [event for case in CASES for event in generate_case(case.scenario_id)]
    assert len(CASES) == 25
    assert len(events) == 7500
    assert len({event.account.account_id for event in events}) == 1500
    assert len({event.source_event_key for event in events}) == 7500
    assert len({event.geospatial.target_region_name for event in events}) == 25
    assert Counter(event.language for event in events) == {"en": 2500, "hi": 2500, "hinglish": 2500}
    assert (
        Counter(event.geospatial.source_location_confidence.value for event in events)[
            "UNAVAILABLE"
        ]
        == 1500
    )
    for case in CASES:
        sources = generate_case(case.scenario_id)
        assert sources == generate_case(case.scenario_id)
        assert sources != generate_case(case.scenario_id, seed=43)
        seen: set[str] = set()
        for event in sources:
            assert event.data_origin.value == "SYNTHETIC_REPLAY"
            assert event.text.startswith("[SYNTHETIC EXERCISE]")
            if event.parent_event_id:
                assert event.parent_event_id.removeprefix("source:") in seen
            seen.add(event.source_event_key)
            assert SourceEvent.model_validate_json(event.model_dump_json()) == event
        assert (sources[-1].timestamp_utc - sources[0].timestamp_utc).total_seconds() < 86400
    # All files are individually usable raw source rows; no labels/scores enter ingestion.
    manifest = json.loads((root / "sample_data/case_pack/manifest.json").read_text("utf-8"))
    assert manifest["total_posts"] == 7500
    assert {entry["generation_pattern"] for entry in manifest["cases"]} == {
        "synchronized",
        "staggered",
        "mixed",
        "mobilization",
        "organic",
    }


def test_scenario_allowlist_and_playback_contract() -> None:
    for case in CASES:
        assert ScenarioSwitchRequest(scenario_id=case.scenario_id).playback_mode == "TIMED"
    assert ScenarioSwitchRequest(scenario_id="expanded", playback_mode="BATCH")
    for value in ("../../outside", "invented-case", ""):
        with pytest.raises(ValidationError):
            ScenarioSwitchRequest(scenario_id=value)
    with pytest.raises(ValidationError):
        ScenarioSwitchRequest(scenario_id="expanded", playback_mode="INVALID")


def test_all_7500_posts_reach_dashboard_snapshots(tmp_path: Path) -> None:
    token = "case-pack-test-" + "x" * 40
    headers = {"Authorization": "Bearer " + token}
    app = create_app(Settings(data_dir=tmp_path, session_token=token))
    started = time.monotonic()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        request = {"scenario_id": "expanded", "playback_mode": "BATCH", "seed": 42}
        assert client.get("/api/v1/campaigns").status_code == 200
        assert (
            client.post(
                "/api/v1/simulate/scenario",
                json={"scenario_id": "unknown"},
                headers=headers,
            ).status_code
            == 422
        )
        accepted = client.post("/api/v1/simulate/scenario", json=request, headers=headers)
        assert accepted.status_code == 202
        job = {}
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            job = client.get(accepted.json()["status_url"], headers=headers).json()
            if job["status"] in {"SUCCEEDED", "FAILED"}:
                break
            time.sleep(0.2)
        assert job["status"] == "SUCCEEDED", job
        state = app.state.workbench
        details = state.list_campaigns()
        assert sum(detail.total_posts for detail in details) == 7500
        assert len({post.event_id for detail in details for post in detail.sample_posts}) == 7500
        assert (
            len({post.account.account_id for detail in details for post in detail.sample_posts})
            == 1500
        )
        assert all(detail.data_origin.value == "SYNTHETIC_REPLAY" for detail in details)
        assert all(detail.claim_verification.status.value == "UNVERIFIED" for detail in details)
        summaries = client.get("/api/v1/campaigns", headers=headers)
        assert summaries.status_code == 200
        assert sum(item["total_posts"] for item in summaries.json()) == 7500
        first = client.get(
            f"/api/v1/campaigns/{details[0].campaign_id}",
            headers=headers,
        )
        assert first.status_code == 200
        print(
            f"Pack analysed in {time.monotonic() - started:.1f}s: "
            f"25 source cases, {len(details)} detected narratives, 7500 posts"
        )
