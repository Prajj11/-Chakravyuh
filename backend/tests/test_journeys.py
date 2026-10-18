import base64
import json
import time
import wave
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
import stix2
from fastapi.testclient import TestClient

from app.config import Settings
from app.evidence.canonical import sha256
from app.jobs.worker import Stream
from app.main import create_app
from app.schemas.models import JobNotification

TOKEN = "integration-test-session-" + "x" * 40
HEADERS = {"Authorization": "Bearer " + TOKEN}


def test_old_injection_is_retained_without_rewriting_active_window(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path, session_token=TOKEN))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        for timestamp in ("2026-10-18T12:00:00Z", "2026-10-16T12:00:00Z"):
            accepted = client.post(
                "/api/v1/events/inject",
                headers=HEADERS,
                json={"text": "An independent observation", "timestamp_utc": timestamp},
            ).json()
            job = wait_job(client, accepted)
        assert job["status"] == "FAILED"
        assert job["error_code"] == "EVENT_RETAINED_OUTSIDE_ACTIVE_WINDOW"
        state = app.state.workbench
        events = state.list_events(state.partitions()[0])
        assert len(events) == 2
        assert min(event.timestamp_utc for event in events) == datetime(
            2026, 10, 16, 12, tzinfo=UTC
        )
        archived = state.evidence.search_events("independent", "local")
        assert len(archived) == 2
        assert archived[0].timestamp_utc == datetime(2026, 10, 16, 12, tzinfo=UTC)
        state.evidence.verify("local")


def wait_job(
    client: TestClient, accepted: dict[str, object], timeout: float = 45
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(str(accepted["status_url"]), headers=HEADERS)
        assert response.status_code == 200
        job = response.json()
        if job["status"] in {"SUCCEEDED", "FAILED"}:
            return job
        time.sleep(0.05)
    pytest.fail("Queued job did not reach a terminal state")


def test_injection_review_isolation_redacted_export_and_corruption(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path, session_token=TOKEN))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        seed = client.post(
            "/api/v1/events/inject",
            headers=HEADERS,
            json={
                "handle": "@ObservedSeed",
                "text": "परीक्षण: Lucknow community observation by @PrivateParticipant.",
                "language": "hi",
                "timestamp_utc": "2026-10-18T11:59:00Z",
            },
        ).json()
        assert wait_job(client, seed)["status"] == "SUCCEEDED"
        for index in range(3):
            accepted = client.post(
                "/api/v1/events/inject",
                headers=HEADERS,
                json={
                    "handle": "@PrivateParticipant",
                    "source_lat": 26.9,
                    "source_lon": 80.9,
                    "text": "परीक्षण: Lucknow community observation by @PrivateParticipant.",
                    "language": "hi",
                    "timestamp_utc": f"2026-10-18T12:0{index * 3}:00Z",
                },
            ).json()
            job = wait_job(client, accepted)
            assert job["status"] == "SUCCEEDED", job
        campaign_id = job["result"]["assigned_campaign_id"]
        detail = client.get(f"/api/v1/campaigns/{campaign_id}", headers=HEADERS).json()
        assert detail["data_origin"] == "USER_INJECTED"
        feed = client.get("/api/v1/campaigns", headers=HEADERS)
        assert "PrivateParticipant" not in feed.text
        unmasked = client.get("/api/v1/campaigns?redact_pii=false", headers=HEADERS)
        assert "PrivateParticipant" in unmasked.text
        assert detail["claim_verification"]["candidate_reference"] is None
        assert (
            client.put(
                f"/api/v1/campaigns/{campaign_id}/claim-review",
                headers=HEADERS,
                json={
                    "reference_id": "synthetic-advisory-0",
                    "status": "CORROBORATED",
                    "analyst_note": "Synthetic references cannot support this origin.",
                },
            ).status_code
            == 400
        )
        accepted = client.post(
            f"/api/v1/campaigns/{campaign_id}/export", headers=HEADERS, json={}
        ).json()
        exported = wait_job(client, accepted)
        assert exported["status"] == "SUCCEEDED", exported
        download = client.get(exported["artifact_download_url"], headers=HEADERS)
        assert download.status_code == 200
        with ZipFile(BytesIO(download.content)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            for name, entry in manifest["files"].items():
                assert sha256(archive.read(name)) == entry["sha256"]
            for name in archive.namelist():
                assert not name.startswith("originals/")
                assert b"PrivateParticipant" not in archive.read(name)
            stix = stix2.parse(archive.read("stix.json").decode(), allow_custom=True)
            observations = json.loads(archive.read("observations.json"))
            for post in observations["sample_posts"]:
                if post["account"]["handle"].startswith("Participant_"):
                    assert post["geospatial"]["source_lat"] is None
                    assert post["geospatial"]["source_h3_index"] is None
            for obj in stix.objects:
                if obj.type == "artifact":
                    assert b"PrivateParticipant" not in base64.b64decode(obj.payload_bin)
            assert archive.read("report.pdf").startswith(b"%PDF")
            (tmp_path / "report.pdf").write_bytes(archive.read("report.pdf"))
        retained_event = app.state.repository.get_event(
            detail["sample_posts"][0]["event_id"], "local"
        )
        path = (
            app.state.repository.store.root
            / retained_event.raw_payload_sha256[:2]
            / retained_event.raw_payload_sha256
        )
        path.write_bytes(b"corrupted")
        blocked = wait_job(
            client,
            client.post(f"/api/v1/campaigns/{campaign_id}/export", headers=HEADERS, json={}).json(),
        )
        assert (
            blocked["status"] == "FAILED" and blocked["error_code"] == "EVIDENCE_INTEGRITY_MISMATCH"
        )


def test_replay_and_contextual_review(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path, session_token=TOKEN))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        accepted = client.post(
            "/api/v1/simulate/scenario",
            headers=HEADERS,
            json={"scenario_id": "cmp_electoral_01", "speed_multiplier": 100},
        ).json()
        job = wait_job(client, accepted)
        assert job["status"] == "SUCCEEDED", job
        campaigns = client.get("/api/v1/campaigns", headers=HEADERS).json()
        assert sum(campaign["total_posts"] for campaign in campaigns) == 108
        selected = next(
            campaign
            for campaign in campaigns
            if campaign["claim_verification"]["candidate_reference"]
        )
        candidate = selected["claim_verification"]["candidate_reference"]
        review = client.put(
            f"/api/v1/campaigns/{selected['campaign_id']}/claim-review",
            headers=HEADERS,
            json={
                "reference_id": candidate["reference_id"],
                "status": "CONTEXT_MISSING",
                "analyst_note": "The fictional advisory lacks media context for a final finding.",
            },
        )
        assert review.status_code == 200, review.text
        assert review.json()["reviewed_by"].startswith("local-analyst:")
        assert review.json()["status"] == "CONTEXT_MISSING"
        assert app.state.repository.verify("local")["events"] >= 108


def test_stream_retention_and_websocket_auth(tmp_path: Path) -> None:
    stream = Stream()
    for index in range(1002):
        stream.publish(
            "JOB_UPDATED", JobNotification(job_id=str(index), status="FAILED"), "job failed"
        )
    recovered = stream.recover(1, ["active"])
    assert recovered[-1].message_type == "SCENARIO_RESET"
    assert recovered[-1].payload.loaded_campaign_ids == ["active"]
    assert all(message.sequence > 1000 for message in stream.recover(1000, ["active"]))
    app = create_app(Settings(data_dir=tmp_path, session_token=TOKEN))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        with client.websocket_connect(
            "ws://127.0.0.1/ws/stream", subprotocols=["chakravyuh.v1", TOKEN]
        ) as websocket:
            accepted = client.post(
                "/api/v1/events/inject", headers=HEADERS, json={"text": "One observed event"}
            ).json()
            message = websocket.receive_json()
            assert message["message_type"] == "NEW_EVENT"
            assert message["sequence"] >= 1
            assert wait_job(client, accepted)["status"] == "SUCCEEDED"


def test_reset_during_replay_cancels_stale_job(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path, session_token=TOKEN))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        old = client.post(
            "/api/v1/simulate/scenario",
            headers=HEADERS,
            json={"scenario_id": "cmp_electoral_01", "seed": 42, "speed_multiplier": 1},
        ).json()
        time.sleep(0.2)
        replacement = client.post(
            "/api/v1/simulate/scenario",
            headers=HEADERS,
            json={"scenario_id": "cmp_geo_astroturf_02", "seed": 43, "speed_multiplier": 100},
        ).json()
        assert wait_job(client, old)["error_code"] == "GENERATION_RESET"
        assert wait_job(client, replacement)["status"] == "SUCCEEDED"
        details = app.state.workbench.list_campaigns()
        assert sum(detail.total_posts for detail in details) == 45
        assert all(
            "cmp_electoral_01" not in event.account.account_id
            for detail in details
            for event in detail.sample_posts
        )


def test_retained_audio_reports_unsupported(tmp_path: Path) -> None:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\0" * 160)
    app = create_app(Settings(data_dir=tmp_path, session_token=TOKEN))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        uploaded = client.post(
            "/api/v1/media",
            headers=HEADERS,
            files={"file": ("audio.wav", buffer.getvalue(), "audio/wav")},
        )
        assert uploaded.status_code == 201
        accepted = client.post(
            "/api/v1/forensics/verify-media",
            headers=HEADERS,
            json={"media_artifact_id": uploaded.json()["media_artifact_id"]},
        ).json()
        result = wait_job(client, accepted)
        assert result["status"] == "SUCCEEDED"
        assert result["result"]["analysis_status"] == "UNSUPPORTED"
        assert result["result"]["deepfake_visual_score"] is None
