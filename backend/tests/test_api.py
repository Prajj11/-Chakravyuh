from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from starlette.websockets import WebSocketDisconnect

from app.config import Settings
from app.main import create_app

TOKEN = "test-session-token-32-characters-minimum"


def test_direct_local_access_without_token(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert not (tmp_path / "local-session-token").exists()
        assert client.get("/api/v1/campaigns").status_code == 200
        assert client.get("/api/v1/collectors").status_code == 200
        upload = client.post("/api/v1/media", files={"file": ("image.png", png(), "image/png")})
        assert upload.status_code == 201
        artifact_id = upload.json()["media_artifact_id"]
        assert client.get(f"/api/v1/artifacts/{artifact_id}/download").content == png()
        accepted = client.post(
            "/api/v1/events/inject",
            json={"handle": "@local", "text": "Direct local observation"},
        )
        assert accepted.status_code == 202
        with client.websocket_connect("ws://127.0.0.1/ws/stream") as socket:
            assert socket.accepted_subprotocol is None
        with pytest.raises(WebSocketDisconnect) as rejected:
            with client.websocket_connect(
                "ws://127.0.0.1/ws/stream", headers={"Origin": "https://outside.example"}
            ):
                pass
        assert rejected.value.code == 4403


def png() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (16, 16), "blue").save(stream, format="PNG")
    return stream.getvalue()


def test_api_home_points_to_configured_workbench(tmp_path: Path) -> None:
    app = create_app(
        Settings(data_dir=tmp_path, session_token=TOKEN, frontend_origin="http://127.0.0.1:3456")
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        home = client.get("/")
        assert home.status_code == 200
        assert home.headers["content-type"].startswith("text/html")
        assert "Chakravyuh API is running" in home.text
        assert "href='http://127.0.0.1:3456'" in home.text
        assert "href='/docs'" in home.text
        assert TOKEN not in home.text
        assert client.get("/api/v1/campaigns").status_code == 200


def test_tokenless_json_still_requires_a_valid_body(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path, session_token=TOKEN))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/v1/events/inject",
            content=b"{not-json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422


def test_chunked_upload_body_is_bounded_before_spooling(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path, session_token=TOKEN, upload_limit_bytes=1024))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/v1/media",
            headers={
                "Authorization": "Bearer " + TOKEN,
                "Content-Type": "multipart/form-data; boundary=boundary",
            },
            content=iter(
                [
                    b"--boundary\r\nContent-Disposition: form-data; "
                    b'name="file"; filename="big.png"\r\nContent-Type: image/png\r\n\r\n',
                    b"x" * 70000,
                    b"\r\n--boundary--\r\n",
                ]
            ),
        )
        assert response.status_code == 413
        assert response.json()["code"] == "UPLOAD_TOO_LARGE"


def test_health_auth_upload_download_and_cors(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path, session_token=TOKEN))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["layer_status"]["coordination"] == "AVAILABLE"
        assert TOKEN not in health.text
        assert client.get("/api/v1/campaigns").json() == []
        assert client.get("/api/v1/collectors").status_code == 200
        assert client.get("/api/v1/alerts/delivery").status_code == 200
        client.headers["Authorization"] = f"Bearer {TOKEN}"
        assert client.get("/api/v1/collectors").json() == {}
        assert client.get("/api/v1/alerts/delivery").json() == {"enabled": False, "counts": {}}
        assert client.get("/api/v1/campaigns").json() == []
        assert (
            client.get(
                "/api/v1/campaigns", headers={"Origin": "https://outside.example"}
            ).status_code
            == 403
        )
        upload = client.post(
            "/api/v1/media", files={"file": ("../../unsafe.png", png(), "image/png")}
        )
        assert upload.status_code == 201
        artifact_id = upload.json()["media_artifact_id"]
        download = client.get(f"/api/v1/artifacts/{artifact_id}/download")
        assert download.content == png()
        assert "unsafe" not in download.headers["content-disposition"]
        assert download.headers["content-disposition"].endswith('.png"')
        assert download.headers["x-content-type-options"] == "nosniff"
        client.headers.pop("Authorization")
        assert client.get(f"/api/v1/artifacts/{artifact_id}/download").status_code == 200
        assert client.get("/unknown").json()["code"] == "NOT_FOUND"
        allowed = client.options(
            "/api/v1/media",
            headers={"Origin": "http://127.0.0.1:3000", "Access-Control-Request-Method": "POST"},
        )
        assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_foreign_origin_upload_rejected_before_multipart_parsing(tmp_path: Path) -> None:
    with TestClient(
        create_app(Settings(data_dir=tmp_path, session_token=TOKEN)), base_url="http://127.0.0.1"
    ) as client:
        # Reject foreign-site mutations before parsing multipart bytes.
        result = client.post(
            "/api/v1/media",
            content=b"invalid multipart",
            headers={
                "Content-Type": "multipart/form-data; boundary=missing",
                "Content-Length": "99999999",
                "Origin": "https://outside.example",
            },
        )
        assert result.status_code == 403
        assert result.json()["code"] == "ACCESS_DENIED"


@pytest.mark.parametrize("data,mime", [(b"not an image", "image/jpeg"), (png(), "image/jpeg")])
def test_malformed_and_mismatched_uploads(tmp_path: Path, data: bytes, mime: str) -> None:
    with TestClient(
        create_app(Settings(data_dir=tmp_path, session_token=TOKEN)), base_url="http://127.0.0.1"
    ) as client:
        response = client.post(
            "/api/v1/media",
            headers={"Authorization": f"Bearer {TOKEN}"},
            files={"file": ("file.jpg", data, mime)},
        )
        assert response.status_code == 415
        assert response.json()["code"] == "UNSUPPORTED_MEDIA"
        assert response.json()["request_id"]


def test_upload_size_dimensions_and_validation(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path, session_token=TOKEN, upload_limit_bytes=100, image_max_pixels=100
    )
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        client.headers["Authorization"] = f"Bearer {TOKEN}"
        assert (
            client.post(
                "/api/v1/media", files={"file": ("large.png", b"x" * 101, "image/png")}
            ).status_code
            == 413
        )
        assert (
            client.post(
                "/api/v1/media", files={"file": ("pixels.png", png(), "image/png")}
            ).status_code
            == 413
        )
        invalid = client.post("/api/v1/media")
        assert invalid.status_code == 422
        assert invalid.json()["code"] == "VALIDATION_ERROR"


def test_corruption_blocks_artifact_download(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path, session_token=TOKEN))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        client.headers["Authorization"] = f"Bearer {TOKEN}"
        uploaded = client.post(
            "/api/v1/media", files={"file": ("test.png", png(), "image/png")}
        ).json()
        repository = app.state.repository
        repository.store._path(uploaded["sha256_hash"]).write_bytes(b"tampered")
        response = client.get(f"/api/v1/artifacts/{uploaded['media_artifact_id']}/download")
        assert response.status_code == 409
        assert response.json()["code"] == "EVIDENCE_INTEGRITY_MISMATCH"
