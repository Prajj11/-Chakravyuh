"""Loopback FastAPI entry point for the evidence foundation."""

import asyncio
import json
import logging
import secrets
import wave
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from html import escape
from io import BytesIO
from uuid import uuid4

from fastapi import Depends, FastAPI, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from PIL import Image, UnidentifiedImageError
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import mount_routes
from app.api.security import UploadBodyLimit
from app.config import Parameters, Settings
from app.evidence.canonical import sha256
from app.evidence.store import IntegrityMismatch
from app.ingestion.live import Feed, Monitor
from app.jobs.worker import Worker
from app.pipeline import Pipeline
from app.reporting.delivery import AlertDelivery
from app.repositories.evidence import EvidenceRepository
from app.repositories.state import StaleGenerationError, StateRepository
from app.schemas.models import (
    AnalysisStatus,
    APIError,
    DataOrigin,
    HealthStatusResponse,
    MediaUploadResponse,
)

logger = logging.getLogger("chakravyuh")


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime = settings or Settings()
    parameters = Parameters()
    token = (
        runtime.session_token.get_secret_value()
        if runtime.session_token
        else secrets.token_urlsafe(32)
    )
    scope = "local"

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        repository = EvidenceRepository(runtime.data_dir, parameters)
        application.state.repository = repository
        worker = None
        monitor = None
        delivery = None
        token_file = runtime.data_dir / "local-session-token"
        try:
            state = StateRepository(repository, scope)
            pipeline = await asyncio.to_thread(
                Pipeline,
                state,
                cached_model=runtime.cached_model_dir,
                image_model=runtime.image_model_dir,
            )
            worker = Worker(pipeline)
            application.state.workbench = state
            application.state.worker = worker
            worker.start()
            feeds = (
                [
                    Feed.model_validate(value)
                    for value in json.loads(runtime.live_feeds_file.read_text(encoding="utf-8"))
                ]
                if runtime.live_feeds_file
                else []
            )
            delivery = AlertDelivery(
                repository,
                runtime.alert_webhook_url.get_secret_value() if runtime.alert_webhook_url else None,
                runtime.alert_webhook_secret.get_secret_value()
                if runtime.alert_webhook_secret
                else None,
            )
            application.state.delivery = delivery
            delivery.start()
            monitor = Monitor(worker, feeds, delivery)
            application.state.monitor = monitor
            monitor.start()
            application.state.layer_status = {
                name: AnalysisStatus.AVAILABLE
                for name in (
                    "ingestion",
                    "nlp_engine",
                    "coordination",
                    "graph_engine",
                    "geo_engine",
                    "media_forensics",
                    "reporting",
                )
            }
            # Read the launch token locally; never expose it through HTTP.
            token_file = runtime.data_dir / "local-session-token"
            token_file.write_text(token, encoding="utf-8")
            logger.info("Local session token saved at %s", token_file)
            yield
        finally:
            if monitor is not None:
                await monitor.close()
            if delivery is not None:
                await delivery.close()
            if worker is not None:
                await worker.close()
            repository.close()
            if token_file.exists() and token_file.read_text(encoding="utf-8") == token:
                token_file.unlink()

    application = FastAPI(title="Chakravyuh", version="2.1.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[runtime.frontend_origin],
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    application.add_middleware(UploadBodyLimit, limit=runtime.upload_limit_bytes + 65536)

    @application.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = uuid4().hex
        if request.method in {"POST", "PUT"} and request.url.path.startswith("/api/v1/"):
            # Authenticate JSON and multipart mutations before FastAPI body parsing.
            if not secrets.compare_digest(
                request.headers.get("authorization", ""), "Bearer " + token
            ):
                return error(
                    request, 401, "SESSION_REQUIRED", "A valid local session token is required"
                )
            if request.headers.get("origin") not in {None, runtime.frontend_origin}:
                return error(request, 403, "ACCESS_DENIED", "Origin is outside this local session")
        if request.method == "POST" and request.url.path == "/api/v1/media":
            # FastAPI parses multipart before dependency resolution. Authenticate here as well
            # to reject unauthorized bodies before the parser can spool them to disk.
            if not secrets.compare_digest(
                request.headers.get("authorization", ""), "Bearer " + token
            ):
                return error(
                    request, 401, "SESSION_REQUIRED", "A valid local session token is required"
                )
            declared_length = request.headers.get("content-length")
            if declared_length is not None:
                try:
                    body_length = int(declared_length)
                except ValueError:
                    return error(request, 400, "INVALID_CONTEXT", "Invalid Content-Length")
                if body_length > runtime.upload_limit_bytes + 65536:
                    return error(request, 413, "UPLOAD_TOO_LARGE", "Upload exceeds body limit")
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    def error(request: Request, status: int, code: str, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content=APIError(
                code=code,
                message=message,
                request_id=getattr(request.state, "request_id", uuid4().hex),
            ).model_dump(),
        )

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        codes = {
            400: "INVALID_CONTEXT",
            401: "SESSION_REQUIRED",
            403: "ACCESS_DENIED",
            404: "NOT_FOUND",
            409: "CONFLICT",
            413: "UPLOAD_TOO_LARGE",
            415: "UNSUPPORTED_MEDIA",
        }
        return error(
            request, exc.status_code, codes.get(exc.status_code, "HTTP_ERROR"), str(exc.detail)
        )

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error(
            request, 422, "VALIDATION_ERROR", "Request does not match the expected contract"
        )

    @application.exception_handler(IntegrityMismatch)
    async def integrity_error(request: Request, exc: IntegrityMismatch) -> JSONResponse:
        return error(
            request, 409, "EVIDENCE_INTEGRITY_MISMATCH", "Evidence integrity verification failed"
        )

    @application.exception_handler(OverflowError)
    async def queue_full(request: Request, exc: OverflowError) -> JSONResponse:
        return error(
            request, 429, "QUEUE_FULL", "Local job queue is full; retry after current jobs finish"
        )

    @application.exception_handler(StaleGenerationError)
    async def stale_generation(request: Request, exc: StaleGenerationError) -> JSONResponse:
        return error(
            request, 409, "GENERATION_RESET", "Replay changed; refresh the campaign before retrying"
        )

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Request failed request_id=%s exception_type=%s",
            request.state.request_id,
            type(exc).__name__,
        )
        return error(request, 500, "INTERNAL_ERROR", "The request could not be completed")

    def session(request: Request) -> str:
        authorization = request.headers.get("authorization", "")
        if not secrets.compare_digest(authorization, "Bearer " + token):
            raise HTTPException(401, "A valid local session token is required")
        origin = request.headers.get("origin")
        if origin is not None and origin != runtime.frontend_origin:
            raise HTTPException(403, "Origin is outside this local session")
        return "local-analyst:" + sha256(token.encode())[:12]

    @application.get("/", response_class=HTMLResponse, include_in_schema=False)
    def api_home() -> HTMLResponse:
        workbench = escape(runtime.frontend_origin, quote=True)
        return HTMLResponse(
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Chakravyuh API</title><style>"
            "body{font:17px/1.6 system-ui,sans-serif;background:#0b1220;color:#e2e8f0;"
            "max-width:700px;margin:12vh auto;padding:24px}"
            "h1{line-height:1.2}a{color:#7dd3fc}code{color:#a5f3fc}"
            ".open{display:inline-block;background:#38bdf8;color:#082033;padding:12px 20px;"
            "border-radius:8px;text-decoration:none;font-weight:700}"
            "nav{display:flex;gap:24px;margin-top:24px}</style></head><body>"
            "<h1>Chakravyuh API is running</h1>"
            "<p>Open the investigation workbench to use the app:</p>"
            f"<p><a class='open' href='{workbench}'>Open Chakravyuh workbench</a></p>"
            f"<p>Workbench address: <a href='{workbench}'>{workbench}</a></p>"
            "<p>If it is unavailable, double-click <code>start.bat</code> to start both services, "
            "or <code>start-frontend.bat</code> to start the frontend separately.</p>"
            "<nav aria-label='API resources'><a href='/docs'>API documentation</a>"
            "<a href='/api/v1/health'>API health</a></nav></body></html>"
        )

    @application.get("/api/v1/health", response_model=HealthStatusResponse)
    def health(request: Request) -> HealthStatusResponse:
        repository: EvidenceRepository = request.app.state.repository
        layers = dict(request.app.state.layer_status)
        collector_status = request.app.state.monitor.status
        if collector_status:
            layers["live_collection"] = (
                AnalysisStatus.AVAILABLE
                if all(item["state"] == "POLLING" for item in collector_status.values())
                else AnalysisStatus.FAILED
                if any(item["state"] == "BACKOFF" for item in collector_status.values())
                else AnalysisStatus.PENDING
            )
        return HealthStatusResponse(
            status="healthy"
            if all(status == AnalysisStatus.AVAILABLE for status in layers.values())
            else "degraded",
            active_campaigns_count=len(request.app.state.workbench.list_campaigns()),
            total_ingested_events=repository.event_count(scope),
            layer_status=layers,
        )

    @application.post("/api/v1/media", response_model=MediaUploadResponse, status_code=201)
    def upload_media(
        request: Request, file: UploadFile, actor: str = Depends(session)
    ) -> MediaUploadResponse:
        data = file.file.read(runtime.upload_limit_bytes + 1)
        if len(data) > runtime.upload_limit_bytes:
            raise HTTPException(413, "Upload exceeds the 25 MiB limit")
        formats = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
        if len(data) >= 12 and data[4:8] == b"ftyp":
            from app.media_forensics.av import inspect_bytes

            if file.content_type not in {"video/mp4", "application/octet-stream"}:
                raise HTTPException(415, "Declared MIME type does not match MP4")
            try:
                inspect_bytes(data, "video/mp4")
            except ValueError as exc:
                raise HTTPException(415, "Unsupported, oversized or malformed video") from exc
            video_repository: EvidenceRepository = request.app.state.repository
            with video_repository.transaction() as db:
                artifact_id, digest = video_repository.put_artifact(
                    db, data, "MEDIA", "video/mp4", DataOrigin.USER_INJECTED, scope
                )
                video_repository.append_audit(
                    db,
                    action="MEDIA_COLLECTED",
                    origin=DataOrigin.USER_INJECTED,
                    actor_id=actor,
                    media_sha256=[digest],
                )
            return MediaUploadResponse(
                media_artifact_id=artifact_id, sha256_hash=digest, media_type="video"
            )
        # Retain structurally valid WAV containers; absence of an audio model remains UNSUPPORTED.
        if data.startswith(b"RIFF") and data[8:12] == b"WAVE":
            try:
                with wave.open(BytesIO(data), "rb") as audio:
                    expected = audio.getnframes() * audio.getnchannels() * audio.getsampwidth()
                    if expected <= 0 or len(audio.readframes(audio.getnframes())) != expected:
                        raise ValueError("Truncated WAV")
            except (wave.Error, EOFError, ValueError) as exc:
                raise HTTPException(415, "Malformed WAV audio") from exc
            if file.content_type not in {"audio/wav", "audio/x-wav", "application/octet-stream"}:
                raise HTTPException(415, "Declared MIME type does not match WAV container")
            audio_repository: EvidenceRepository = request.app.state.repository
            with audio_repository.transaction() as db:
                artifact_id, digest = audio_repository.put_artifact(
                    db, data, "MEDIA", "audio/wav", DataOrigin.USER_INJECTED, scope
                )
                audio_repository.append_audit(
                    db,
                    action="MEDIA_COLLECTED",
                    origin=DataOrigin.USER_INJECTED,
                    actor_id=actor,
                    media_sha256=[digest],
                )
            return MediaUploadResponse(
                media_artifact_id=artifact_id, sha256_hash=digest, media_type="audio"
            )
        try:
            with Image.open(BytesIO(data)) as image:
                mime = formats.get(image.format or "")
                if mime is None:
                    raise HTTPException(415, "Supported uploads in this slice: JPEG, PNG and WebP")
                if image.width * image.height > runtime.image_max_pixels:
                    raise HTTPException(413, "Decoded image dimensions exceed the limit")
                image.verify()
            with Image.open(BytesIO(data)) as image:
                image.load()
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise HTTPException(413, "Decoded image dimensions exceed the limit") from exc
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
            raise HTTPException(415, "Malformed or unsupported image") from exc
        if file.content_type not in {mime, "application/octet-stream"}:
            raise HTTPException(415, "Declared MIME type does not match decoded content")
        repository: EvidenceRepository = request.app.state.repository
        with repository.transaction() as db:
            artifact_id, digest = repository.put_artifact(
                db, data, "MEDIA", mime, DataOrigin.USER_INJECTED, scope
            )
            repository.append_audit(
                db,
                action="MEDIA_COLLECTED",
                origin=DataOrigin.USER_INJECTED,
                actor_id=actor,
                media_sha256=[digest],
            )
        return MediaUploadResponse(
            media_artifact_id=artifact_id, sha256_hash=digest, media_type="image"
        )

    @application.get("/api/v1/artifacts/{artifact_id}/download", dependencies=[Depends(session)])
    def artifact_download(request: Request, artifact_id: str) -> Response:
        repository: EvidenceRepository = request.app.state.repository
        try:
            data, mime, _ = repository.artifact(artifact_id, scope)
        except KeyError as exc:
            raise HTTPException(404, "Unknown artifact") from exc
        return Response(
            data,
            media_type=mime,
            headers={
                "Content-Disposition": f'attachment; filename="{artifact_id}{extension(mime)}"'
            },
        )

    mount_routes(application, session, token, runtime.frontend_origin)
    return application


app = create_app()


def extension(mime: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
        "application/zip": ".zip",
        "application/json": ".json",
        "text/html": ".html",
        "video/mp4": ".mp4",
        "audio/wav": ".wav",
        "audio/mpeg": ".mp3",
    }.get(mime, ".bin")
