from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event

import pytest

from app.ingestion.contracts import SourceEvent
from app.ingestion.service import IngestionService
from app.repositories.evidence import EvidenceRepository
from app.repositories.state import (
    GeoBaselineBucket,
    StaleGenerationError,
    StatePartition,
    StateRepository,
)
from app.schemas.models import DataOrigin, EventInjectRequest, JobStatusResponse


def test_reset_preserves_evidence_and_other_partitions(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    state = StateRepository(repository, "test")
    ingestor = IngestionService(repository)
    public = StatePartition(data_origin=source.data_origin, collector_scope=source.collector_scope)
    replay = StatePartition(data_origin=DataOrigin.SYNTHETIC_REPLAY, collector_scope="replay")
    a = ingestor.ingest(source, scope="test")
    b = ingestor.ingest(
        source.model_copy(update={"data_origin": replay.data_origin, "collector_scope": "replay"}),
        scope="test",
    )
    state.record_account(public, 0, a.event_id)
    state.record_account(replay, 0, b.event_id)
    job = state.create_job(replay, 0, EventInjectRequest(text="queued operation"))
    assert state.reset_replay("replay") == 1
    assert state.list_events(replay) == []
    assert state.list_events(public) == [a]
    assert state.get_job(job.job_id).error_code == "GENERATION_RESET"
    with pytest.raises(StaleGenerationError):
        state.record_account(replay, 0, b.event_id)
    assert repository.verify("test")["events"] == 2
    with pytest.raises(ValueError):
        state.record_account(replay, 1, a.event_id)


def test_durable_jobs_recover_and_scopes_cannot_read_them(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    partition = StatePartition(
        data_origin=source.data_origin, collector_scope=source.collector_scope
    )
    state = StateRepository(repository, "test")
    job = state.create_job(partition, 0, EventInjectRequest(text="input"))
    state.update_job(JobStatusResponse(job_id=job.job_id, job_type="INJECT", status="RUNNING"))
    other = StateRepository(repository, "other")
    with pytest.raises(KeyError):
        other.get_job(job.job_id)
    reopened = StateRepository(repository, "test")
    assert reopened.get_job(job.job_id).error_code == "PROCESS_RESTART"


def test_reset_serializes_with_mutation(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    state = StateRepository(repository)
    replay = StatePartition(data_origin=DataOrigin.SYNTHETIC_REPLAY, collector_scope="replay")
    state.generation(replay)
    started = Event()

    def reset() -> int:
        started.set()
        return state.reset_replay("replay")

    with ThreadPoolExecutor(1) as pool:
        with state.mutation(replay, 0):
            future = pool.submit(reset)
            assert started.wait(timeout=2)
            assert not future.done()
        assert future.result(timeout=2) == 1
    with pytest.raises(StaleGenerationError):
        with state.mutation(replay, 0):
            pytest.fail("An obsolete worker entered a mutation")


def test_baseline_scope_and_hour_validation(
    repository: EvidenceRepository, source: SourceEvent
) -> None:
    state = StateRepository(repository)
    partition = StatePartition(data_origin=source.data_origin, collector_scope="one")
    other = StatePartition(data_origin=source.data_origin, collector_scope="two")
    bucket = GeoBaselineBucket(
        topic_family_id="topic",
        h3_index="853d8dcffffffff",
        hour_utc=source.timestamp_utc,
        count=0,
        collection_coverage=1,
    )
    state.put_baseline_bucket(partition, bucket)
    assert state.list_baseline_buckets(partition) == [bucket]
    assert state.list_baseline_buckets(other) == []
    with pytest.raises(ValueError):
        state.put_baseline_bucket(
            partition,
            bucket.model_copy(update={"hour_utc": bucket.hour_utc + timedelta(seconds=1)}),
        )
