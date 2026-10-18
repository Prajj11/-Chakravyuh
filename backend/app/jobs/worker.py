"""Single mutation queue; CPU work stays in an executor and publications check generation."""

import asyncio
import logging
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from functools import partial
from typing import ParamSpec, TypeVar

from app.evidence.store import IntegrityMismatch
from app.ingestion.clock import ReplayClock
from app.ingestion.contracts import SourceEvent
from app.ingestion.simulator import SCENARIO_IDS, load_scenario, retain_source
from app.pipeline import Pipeline
from app.reporting.exporter import Exporter
from app.repositories.state import JobRequest, StaleGenerationError, StatePartition
from app.schemas.models import (
    CampaignAlert,
    DataOrigin,
    EventInjectRequest,
    ExportRequest,
    ForensicsVerifyRequest,
    JobAccepted,
    JobNotification,
    JobStatusResponse,
    ScenarioSwitchRequest,
    ScenarioSwitchResponse,
    UnifiedSocialEventEnriched,
    WebSocketStreamMessage,
)

logger = logging.getLogger("chakravyuh.jobs")
P = ParamSpec("P")
R = TypeVar("R")


class Stream:
    def __init__(self) -> None:
        self.sequence = 0
        self.messages: deque[WebSocketStreamMessage] = deque(maxlen=1000)
        self.listeners: set[asyncio.Queue[WebSocketStreamMessage]] = set()

    def publish(
        self, kind: str, payload: object, headline: str, campaign_id: str | None = None
    ) -> WebSocketStreamMessage:
        self.sequence += 1
        message = WebSocketStreamMessage.model_validate(
            {
                "sequence": self.sequence,
                "message_type": kind,
                "timestamp_utc": datetime.now(UTC),
                "campaign_id": campaign_id,
                "headline": headline,
                "payload": payload,
            }
        )
        self.messages.append(message)
        for listener in tuple(self.listeners):
            if listener.full():
                self.listeners.remove(listener)
            else:
                listener.put_nowait(message)
        return message

    def recover(self, last_sequence: int, campaign_ids: list[str]) -> list[WebSocketStreamMessage]:
        if last_sequence > self.sequence or (
            self.messages and last_sequence < self.messages[0].sequence - 1
        ):
            reset = self.publish(
                "SCENARIO_RESET",
                ScenarioSwitchResponse(
                    scenario_id="resync", loaded_campaign_ids=campaign_ids, reset_state=False
                ),
                "Stream history expired; resync campaign snapshots",
            )
            return [reset]
        return [message for message in self.messages if message.sequence > last_sequence]


class Worker:
    def __init__(self, pipeline: Pipeline) -> None:
        self.pipeline = pipeline
        self.state = pipeline.state
        self.stream = Stream()
        self.queue: asyncio.Queue[tuple[str, str | None, str]] = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="chakravyuh-cpu")
        self.task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self.task = asyncio.create_task(self.run())

    async def close(self) -> None:
        if self.task is not None:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        await asyncio.to_thread(self.executor.shutdown, wait=True, cancel_futures=True)

    async def cpu(self, function: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        return await asyncio.get_running_loop().run_in_executor(
            self.executor, partial(function, *args, **kwargs)
        )

    def submit(
        self, request: JobRequest, actor: str, campaign_id: str | None = None
    ) -> JobAccepted:
        if self.queue.qsize() >= 100:
            raise OverflowError("Local job queue is full")
        if isinstance(request, ScenarioSwitchRequest):
            partition = StatePartition(
                data_origin=DataOrigin.SYNTHETIC_REPLAY, collector_scope="replay-control"
            )
            if request.reset_state:
                replay_ids = {
                    detail.campaign_id
                    for detail in self.state.list_campaigns()
                    if detail.data_origin == DataOrigin.SYNTHETIC_REPLAY
                }
                for old in self.state.partitions():
                    if (
                        old.data_origin == DataOrigin.SYNTHETIC_REPLAY
                        and old.collector_scope != "replay-control"
                    ):
                        self.state.reset_replay(old.collector_scope)
                self.state.reset_replay("replay-control")
                for campaign in replay_ids:
                    self.pipeline.alerts.pop(campaign, None)
        elif isinstance(request, ExportRequest):
            detail = self.state.get_campaign(campaign_id or "")
            event = detail.sample_posts[0]
            from app.ingestion.contracts import CaptureManifest

            manifest, _, _ = self.state.evidence.artifact(
                event.raw_capture_manifest_ref, self.state.scope
            )
            partition = StatePartition(
                data_origin=event.data_origin,
                collector_scope=CaptureManifest.model_validate_json(manifest).collector_scope,
            )
        else:
            partition = StatePartition(
                data_origin=DataOrigin.USER_INJECTED, collector_scope="injected-v1"
            )
        generation = self.state.generation(partition)
        job = self.state.create_job(partition, generation, request)
        self.queue.put_nowait((job.job_id, campaign_id, actor))
        if isinstance(request, ScenarioSwitchRequest) and request.reset_state:
            self.stream.publish(
                "SCENARIO_RESET",
                ScenarioSwitchResponse(
                    scenario_id=request.scenario_id,
                    loaded_campaign_ids=[
                        detail.campaign_id for detail in self.state.list_campaigns()
                    ],
                    reset_state=True,
                ),
                "Replay generation reset; retained evidence preserved",
            )
        return JobAccepted(job_id=job.job_id, status_url=f"/api/v1/jobs/{job.job_id}")

    async def run(self) -> None:
        while True:
            job_id, campaign_id, actor = await self.queue.get()
            try:
                await self.execute(job_id, campaign_id, actor)
            finally:
                self.queue.task_done()

    async def execute(self, job_id: str, campaign_id: str | None, actor: str) -> None:
        record = self.state.get_job_record(job_id)
        try:
            self.state.check(record.partition, record.generation)
            self.state.update_job(record.response.model_copy(update={"status": "RUNNING"}))
            request = record.request
            url = None
            result: object
            if isinstance(request, ScenarioSwitchRequest):
                await self.cpu(self.pipeline.history, request.seed)
                scenarios = SCENARIO_IDS if request.scenario_id == "all" else (request.scenario_id,)
                sources = sorted(
                    [
                        source
                        for scenario in scenarios
                        for source in load_scenario(scenario, request.seed)
                    ],
                    key=lambda source: (source.timestamp_utc, source.source_event_key),
                )
                clock = ReplayClock(
                    sources[0].timestamp_utc,
                    generation=record.generation,
                    speed=request.speed_multiplier,
                    end=sources[-1].timestamp_utc,
                )
                parents: dict[str, str] = {}
                generations = {
                    source.collector_scope: self.state.generation(
                        StatePartition(
                            data_origin=source.data_origin, collector_scope=source.collector_scope
                        )
                    )
                    for source in sources
                }
                while sources:
                    self.state.check(record.partition, record.generation)
                    delay = clock.delay_until(
                        sources[0].timestamp_utc, generation=record.generation
                    )
                    if delay > 0:
                        await asyncio.sleep(min(delay, 0.1))
                        continue
                    batch = []
                    while sources and sources[0].timestamp_utc <= clock.now():
                        batch.append(sources.pop(0))
                    replay_alerts = await self.cpu(
                        self.replay_batch,
                        batch,
                        parents,
                        generations,
                        record.partition,
                        record.generation,
                    )
                    self.state.check(record.partition, record.generation)
                    # Reads use coherent snapshots; event messages carry typed enrichment.
                    for alert in replay_alerts:
                        self.stream.publish(
                            "CTI_ALERT", alert, "Gated campaign warning", alert.campaign_id
                        )
                    for source in batch:
                        details = self.state.list_campaigns()
                        event = self.state.evidence.get_event(
                            parents[source.source_event_key], self.state.scope
                        )
                        enriched = self.pipeline.enriched(event, details, [])
                        self.stream.publish(
                            "NEW_EVENT",
                            enriched,
                            "Observed replay event",
                            enriched.assigned_campaign_id,
                        )
                result = ScenarioSwitchResponse(
                    scenario_id=request.scenario_id,
                    loaded_campaign_ids=[
                        detail.campaign_id
                        for detail in self.state.list_campaigns()
                        if detail.data_origin == DataOrigin.SYNTHETIC_REPLAY
                    ],
                    reset_state=request.reset_state,
                )
            elif isinstance(request, EventInjectRequest):
                enriched, alerts = await self.cpu(self.inject, request, record.generation)
                self.stream.publish(
                    "NEW_EVENT",
                    enriched,
                    "Injected observation analyzed",
                    enriched.assigned_campaign_id,
                )
                for alert in alerts:
                    self.stream.publish(
                        "CTI_ALERT", alert, "Gated campaign warning", alert.campaign_id
                    )
                result = enriched
            elif isinstance(request, ForensicsVerifyRequest):
                result = await self.cpu(self.pipeline.media.verify, request.media_artifact_id)
            else:
                if campaign_id is None:
                    raise ValueError("An export requires a campaign")
                bundle, artifact_id = await self.cpu(
                    Exporter(self.state).export, campaign_id, request, actor
                )
                result = bundle
                url = f"/api/v1/artifacts/{artifact_id}/download"
            self.state.check(record.partition, record.generation)
            response = JobStatusResponse.model_validate(
                {
                    "job_id": job_id,
                    "job_type": record.response.job_type,
                    "status": "SUCCEEDED",
                    "result": result,
                    "artifact_download_url": url,
                }
            )
        except (StaleGenerationError, IntegrityMismatch, ValueError, KeyError) as exc:
            code = (
                "GENERATION_RESET"
                if isinstance(exc, StaleGenerationError)
                else "EVIDENCE_INTEGRITY_MISMATCH"
                if isinstance(exc, IntegrityMismatch)
                else "INVALID_CONTEXT"
            )
            response = JobStatusResponse(
                job_id=job_id, job_type=record.response.job_type, status="FAILED", error_code=code
            )
        except Exception as exc:
            logger.error("Worker failed job=%s exception_type=%s", job_id, type(exc).__name__)
            response = JobStatusResponse(
                job_id=job_id,
                job_type=record.response.job_type,
                status="FAILED",
                error_code="WORKER_FAILED",
            )
        self.state.update_job(response, check_generation=False)
        self.stream.publish(
            "JOB_UPDATED",
            JobNotification.model_validate({"job_id": job_id, "status": response.status}),
            f"{record.response.job_type} {response.status.lower()}",
            campaign_id,
        )

    def replay_batch(
        self,
        sources: list[SourceEvent],
        parents: dict[str, str],
        generations: dict[str, int],
        control: StatePartition,
        control_generation: int,
    ) -> list[CampaignAlert]:
        affected: dict[str, tuple[StatePartition, int]] = {}
        for source in sources:
            partition = StatePartition(
                data_origin=source.data_origin, collector_scope=source.collector_scope
            )
            generation = generations[source.collector_scope]
            with (
                self.state.mutation(control, control_generation),
                self.state.mutation(partition, generation),
            ):
                event = retain_source(
                    source, self.pipeline.ingestor, scope=self.state.scope, parent_ids=parents
                )
                self.state.record_account(partition, generation, event.event_id)
            affected[partition.key] = (partition, generation)
        alerts = []
        for partition, generation in affected.values():
            _, current_alerts = self.pipeline.refresh(partition, generation)
            alerts.extend(current_alerts)
        return alerts

    def inject(
        self, request: EventInjectRequest, generation: int
    ) -> tuple[UnifiedSocialEventEnriched, list[CampaignAlert]]:
        source = self.pipeline.inject_source(request)
        partition = StatePartition(
            data_origin=source.data_origin, collector_scope=source.collector_scope
        )
        event = self.pipeline.activate(source, partition, generation)
        details, alerts = self.pipeline.refresh(partition, generation)
        return self.pipeline.enriched(event, details, alerts), alerts
