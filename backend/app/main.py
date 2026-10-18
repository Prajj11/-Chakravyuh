"""Loopback FastAPI entry point for the evidence foundation."""

import logging
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from PIL import Image, UnidentifiedImageError
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import Parameters, Settings
from app.evidence.canonical import sha256
from app.evidence.store import IntegrityMismatch
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import (
    AnalysisStatus,
    APIError,
    DataOrigin,
    HealthStatusResponse,
    MediaUploadResponse,
    NarrativeCampaignSummary,
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
        # Local user reads this file to authorize this launch. Never expose the token through HTTP.
        token_file = runtime.data_dir / "local-session-token"
        token_file.write_text(token, encoding="utf-8")
        logger.info("Local session token saved at %s", token_file)
        try:
            yield
        finally:
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

    @application.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = uuid4().hex
        if request.method == "POST" and request.url.path == "/api/v1/media":
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

    @application.get("/api/v1/health", response_model=HealthStatusResponse)
    def health(request: Request) -> HealthStatusResponse:
        repository: EvidenceRepository = request.app.state.repository
        return HealthStatusResponse(
            status="degraded",
            active_campaigns_count=0,
            total_ingested_events=repository.event_count(scope),
            layer_status={
                "ingestion": AnalysisStatus.AVAILABLE,
                "nlp_engine": AnalysisStatus.PENDING,
                "coordination": AnalysisStatus.PENDING,
                "graph_engine": AnalysisStatus.PENDING,
                "geo_engine": AnalysisStatus.PENDING,
                "media_forensics": AnalysisStatus.PENDING,
                "reporting": AnalysisStatus.PENDING,
            },
        )

    @application.get(
        "/api/v1/campaigns",
        response_model=list[NarrativeCampaignSummary],
        dependencies=[Depends(session)],
    )
    def campaigns() -> list[NarrativeCampaignSummary]:
        return []

    @application.post("/api/v1/media", response_model=MediaUploadResponse, status_code=201)
    def upload_media(
        request: Request, file: UploadFile, actor: str = Depends(session)
    ) -> MediaUploadResponse:
        data = file.file.read(runtime.upload_limit_bytes + 1)
        if len(data) > runtime.upload_limit_bytes:
            raise HTTPException(413, "Upload exceeds the 25 MiB limit")
        formats = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
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
            headers={"Content-Disposition": f'attachment; filename="{Path(artifact_id).name}.bin"'},
        )

    return application


app = create_app()
