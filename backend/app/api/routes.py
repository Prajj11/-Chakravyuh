"""Typed authenticated API and sequence-recoverable local WebSocket transport."""

import asyncio
from collections.abc import Callable

from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from starlette.exceptions import HTTPException

from app.ingestion.contracts import CaptureManifest
from app.jobs.worker import Worker
from app.nlp_engine.review import review_claim
from app.pipeline import summary
from app.reporting.exporter import PrivacyTransform
from app.repositories.state import StatePartition, StateRepository
from app.schemas.models import (
    ClaimReviewRequest,
    ClaimVerificationAssessment,
    EventInjectRequest,
    ExportRequest,
    ForensicsVerifyRequest,
    JobAccepted,
    JobStatusResponse,
    NarrativeCampaignDetail,
    NarrativeCampaignSummary,
    ScenarioSwitchRequest,
    WebSocketStreamMessage,
)


def mount_routes(
    application: FastAPI, session: Callable[[Request], str], frontend_origin: str
) -> None:
    def state(request: Request) -> StateRepository:
        return request.app.state.workbench

    def worker(request: Request) -> Worker:
        return request.app.state.worker

    @application.get("/api/v1/collectors", dependencies=[Depends(session)])
    def collectors(request: Request) -> dict:
        return request.app.state.monitor.status

    @application.get("/api/v1/alerts/delivery", dependencies=[Depends(session)])
    def deliveries(request: Request) -> dict:
        return request.app.state.delivery.status()

    @application.get(
        "/api/v1/campaigns",
        response_model=list[NarrativeCampaignSummary],
        dependencies=[Depends(session)],
    )
    def campaigns(request: Request, redact_pii: bool = True) -> list[NarrativeCampaignSummary]:
        return [
            NarrativeCampaignSummary.model_validate(
                PrivacyTransform(detail, redact_pii).apply(summary(detail).model_dump(mode="json"))
            )
            for detail in state(request).list_campaigns()
        ]

    @application.get(
        "/api/v1/campaigns/{campaign_id}",
        response_model=NarrativeCampaignDetail,
        dependencies=[Depends(session)],
    )
    def campaign(request: Request, campaign_id: str) -> NarrativeCampaignDetail:
        try:
            return state(request).get_campaign(campaign_id)
        except KeyError as exc:
            raise HTTPException(404, "Unknown campaign") from exc

    @application.get(
        "/api/v1/jobs/{job_id}", response_model=JobStatusResponse, dependencies=[Depends(session)]
    )
    def job(request: Request, job_id: str) -> JobStatusResponse:
        try:
            return state(request).get_job(job_id)
        except KeyError as exc:
            raise HTTPException(404, "Unknown job") from exc

    @application.post("/api/v1/simulate/scenario", response_model=JobAccepted, status_code=202)
    async def scenario(
        request: Request, body: ScenarioSwitchRequest, actor: str = Depends(session)
    ) -> JobAccepted:
        try:
            return worker(request).submit(body, actor)
        except OverflowError as exc:
            raise HTTPException(429, "Local job queue is full") from exc

    @application.post("/api/v1/events/inject", response_model=JobAccepted, status_code=202)
    async def inject(
        request: Request, body: EventInjectRequest, actor: str = Depends(session)
    ) -> JobAccepted:
        return worker(request).submit(body, actor)

    @application.post("/api/v1/forensics/verify-media", response_model=JobAccepted, status_code=202)
    async def verify_media(
        request: Request, body: ForensicsVerifyRequest, actor: str = Depends(session)
    ) -> JobAccepted:
        return worker(request).submit(body, actor)

    @application.post(
        "/api/v1/campaigns/{campaign_id}/export", response_model=JobAccepted, status_code=202
    )
    async def export(
        request: Request, campaign_id: str, body: ExportRequest, actor: str = Depends(session)
    ) -> JobAccepted:
        try:
            return worker(request).submit(body, actor, campaign_id)
        except KeyError as exc:
            raise HTTPException(404, "Unknown campaign") from exc

    @application.put(
        "/api/v1/campaigns/{campaign_id}/claim-review", response_model=ClaimVerificationAssessment
    )
    def claim_review(
        request: Request, campaign_id: str, body: ClaimReviewRequest, actor: str = Depends(session)
    ) -> ClaimVerificationAssessment:
        workbench = state(request)
        try:
            detail = workbench.get_campaign(campaign_id)
            manifest, _, _ = workbench.evidence.artifact(
                detail.sample_posts[0].raw_capture_manifest_ref, workbench.scope
            )
            partition = StatePartition(
                data_origin=detail.data_origin,
                collector_scope=CaptureManifest.model_validate_json(manifest).collector_scope,
            )
            generation = workbench.generation(partition)
            with workbench.mutation(partition, generation):
                detail = workbench.get_campaign(campaign_id)
                assessment = review_claim(workbench, detail, body, actor)
                updated = detail.model_copy(
                    update={
                        "claim_verification": assessment,
                        "snapshot_revision": detail.snapshot_revision + 1,
                    }
                )
                workbench.evidence.record_analysis(
                    updated,
                    [event.canonical_event_sha256 for event in detail.sample_posts],
                    {"review": "contextual-human-review-v1"},
                    detail.data_origin,
                    workbench.scope,
                )
                workbench.put_campaign(partition, generation, updated)
            return assessment
        except KeyError as exc:
            raise HTTPException(404, "Unknown campaign/reference") from exc
        except ValueError as exc:
            raise HTTPException(
                400, "Review does not have a context-valid retained reference"
            ) from exc

    @application.websocket("/ws/stream")
    async def websocket(websocket: WebSocket) -> None:
        protocols = websocket.scope.get("subprotocols", [])
        if websocket.headers.get("origin") not in {None, frontend_origin}:
            await websocket.close(code=4403)
            return
        try:
            last = int(websocket.query_params.get("last_sequence", "0"))
            if last < 0:
                raise ValueError("Invalid sequence")
        except ValueError:
            await websocket.close(code=4400)
            return
        await websocket.accept(
            subprotocol="chakravyuh.v1" if "chakravyuh.v1" in protocols else None
        )
        stream = websocket.app.state.worker.stream
        listener: asyncio.Queue[WebSocketStreamMessage] = asyncio.Queue(maxsize=1000)
        # No await between recovery and subscription, so an update cannot fall in a gap.
        messages = stream.recover(
            last, [detail.campaign_id for detail in websocket.app.state.workbench.list_campaigns()]
        )
        stream.listeners.add(listener)
        try:
            for message in messages:
                await websocket.send_text(message.model_dump_json())
            while listener in stream.listeners:
                receive = asyncio.create_task(websocket.receive())
                update = asyncio.create_task(listener.get())
                done, pending = await asyncio.wait(
                    {receive, update}, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                if receive in done and receive.result().get("type") == "websocket.disconnect":
                    break
                if update in done:
                    await websocket.send_text(update.result().model_dump_json())
        except WebSocketDisconnect:
            pass
        finally:
            stream.listeners.discard(listener)
