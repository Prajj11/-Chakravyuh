"""Durable rebuildable state. Immutable source evidence remains in EvidenceRepository."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import Field

from app.evidence.canonical import canonical_bytes, sha256
from app.ingestion.contracts import CaptureManifest
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import (
    AccountProfile,
    ClaimReference,
    ClaimVerificationAssessment,
    ContractModel,
    DataOrigin,
    EventInjectRequest,
    ExportRequest,
    ForensicsVerifyRequest,
    JobStatusResponse,
    NarrativeCampaignDetail,
    ScenarioSwitchRequest,
    UnifiedSocialEvent,
    UTCDateTime,
)

JobRequest = ScenarioSwitchRequest | EventInjectRequest | ForensicsVerifyRequest | ExportRequest


class StatePartition(ContractModel):
    data_origin: DataOrigin
    collector_scope: str = Field(min_length=1)

    @property
    def key(self) -> str:
        return sha256(canonical_bytes(self))


class GeoBaselineBucket(ContractModel):
    topic_family_id: str
    h3_index: str
    h3_resolution: Literal[5] = 5
    hour_utc: UTCDateTime
    count: int = Field(ge=0)
    collection_coverage: float = Field(ge=0, le=1)


class JobRecord(ContractModel):
    partition: StatePartition
    generation: int
    request: JobRequest
    response: JobStatusResponse


class StaleGenerationError(RuntimeError):
    pass


DDL = """
CREATE TABLE IF NOT EXISTS state_generations (
 scope TEXT, partition_id TEXT, partition_json TEXT, generation INTEGER NOT NULL,
 PRIMARY KEY(scope,partition_id));
CREATE TABLE IF NOT EXISTS active_events (
 scope TEXT, partition_id TEXT, generation INTEGER, event_id TEXT,
 account_json TEXT NOT NULL, PRIMARY KEY(scope,partition_id,generation,event_id));
CREATE TABLE IF NOT EXISTS campaign_memberships (
 scope TEXT, partition_id TEXT, generation INTEGER, campaign_id TEXT, event_id TEXT,
 assigned_at TEXT, pipeline_version TEXT, revision INTEGER,
 PRIMARY KEY(scope,partition_id,generation,campaign_id,event_id));
CREATE TABLE IF NOT EXISTS campaigns (
 scope TEXT, partition_id TEXT, generation INTEGER, campaign_id TEXT,
 revision INTEGER, detail_json TEXT, assessment_hash TEXT,
 PRIMARY KEY(scope,partition_id,generation,campaign_id));
CREATE TABLE IF NOT EXISTS jobs (
 scope TEXT, job_id TEXT, partition_id TEXT, generation INTEGER, record_json TEXT,
 PRIMARY KEY(scope,job_id));
CREATE TABLE IF NOT EXISTS claim_references (
 scope TEXT, reference_id TEXT, reference_json TEXT, PRIMARY KEY(scope,reference_id));
CREATE TABLE IF NOT EXISTS claim_reviews (
 scope TEXT, review_id TEXT, campaign_id TEXT, assessment_json TEXT, audit_entry_id TEXT,
 PRIMARY KEY(scope,review_id));
CREATE TABLE IF NOT EXISTS geo_baseline_buckets (
 scope TEXT, partition_id TEXT, topic_family_id TEXT, h3_index TEXT, hour_utc TEXT,
 bucket_json TEXT, PRIMARY KEY(scope,partition_id,topic_family_id,h3_index,hour_utc));
"""


class StateRepository:
    def __init__(self, evidence: EvidenceRepository, access_scope: str = "local") -> None:
        self.evidence = evidence
        self.scope = access_scope
        with evidence._lock:
            evidence._db.executescript(DDL)
            evidence._db.commit()
        for record in self.list_job_records():
            if record.response.status in {"QUEUED", "RUNNING"}:
                self.update_job(
                    record.response.model_copy(
                        update={"status": "FAILED", "error_code": "PROCESS_RESTART"}
                    ),
                    check_generation=False,
                )

    def generation(self, partition: StatePartition) -> int:
        with self.evidence.transaction() as db:
            db.execute(
                "INSERT OR IGNORE INTO state_generations VALUES (?,?,?,0)",
                (self.scope, partition.key, partition.model_dump_json()),
            )
            row = db.execute(
                "SELECT generation FROM state_generations WHERE scope=? AND partition_id=?",
                (self.scope, partition.key),
            ).fetchone()
            return int(row[0])

    def check(self, partition: StatePartition, generation: int) -> None:
        if self.generation(partition) != generation:
            raise StaleGenerationError("The active replay generation has changed")

    @contextmanager
    def mutation(self, partition: StatePartition, generation: int) -> Iterator[None]:
        with self.evidence._lock:
            self.check(partition, generation)
            yield

    def reset_replay(self, collector_scope: str) -> int:
        partition = StatePartition(
            data_origin=DataOrigin.SYNTHETIC_REPLAY, collector_scope=collector_scope
        )
        with self.evidence._lock:
            generation = self.generation(partition) + 1
            with self.evidence.transaction() as db:
                db.execute(
                    "UPDATE state_generations SET generation=? WHERE scope=? AND partition_id=?",
                    (generation, self.scope, partition.key),
                )
            for record in self.list_job_records():
                if record.partition == partition and record.response.status in {
                    "QUEUED",
                    "RUNNING",
                }:
                    self.update_job(
                        record.response.model_copy(
                            update={"status": "FAILED", "error_code": "GENERATION_RESET"}
                        ),
                        check_generation=False,
                    )
            return generation

    def partitions(self) -> list[StatePartition]:
        with self.evidence._lock:
            rows = self.evidence._db.execute(
                "SELECT partition_json FROM state_generations WHERE scope=?", (self.scope,)
            ).fetchall()
        return [StatePartition.model_validate_json(row[0]) for row in rows]

    def record_account(self, partition: StatePartition, generation: int, event_id: str) -> None:
        with self.mutation(partition, generation):
            event = self.evidence.get_event(event_id, self.scope)
            manifest, _, _ = self.evidence.artifact(event.raw_capture_manifest_ref, self.scope)
            capture = CaptureManifest.model_validate_json(manifest)
            if (
                event.data_origin != partition.data_origin
                or capture.collector_scope != partition.collector_scope
            ):
                raise ValueError("Event is outside this analytical partition")
            with self.evidence.transaction() as db:
                db.execute(
                    "INSERT OR IGNORE INTO active_events VALUES (?,?,?,?,?)",
                    (
                        self.scope,
                        partition.key,
                        generation,
                        event_id,
                        event.account.model_dump_json(),
                    ),
                )

    def list_events(
        self, partition: StatePartition, generation: int | None = None
    ) -> list[UnifiedSocialEvent]:
        active = self.generation(partition) if generation is None else generation
        with self.evidence._lock:
            rows = self.evidence._db.execute(
                "SELECT event_id FROM active_events WHERE scope=? "
                "AND partition_id=? AND generation=?",
                (self.scope, partition.key, active),
            ).fetchall()
            events = [self.evidence.get_event(row[0], self.scope) for row in rows]
        return sorted(events, key=lambda event: (event.timestamp_utc, event.event_id))

    def list_accounts(self, partition: StatePartition) -> list[AccountProfile]:
        return list(
            {
                event.account.account_id: event.account for event in self.list_events(partition)
            }.values()
        )

    def put_campaign(
        self, partition: StatePartition, generation: int, detail: NarrativeCampaignDetail
    ) -> None:
        with self.mutation(partition, generation):
            if detail.data_origin != partition.data_origin:
                raise ValueError("Campaign origin differs from partition")
            with self.evidence.transaction() as db:
                previous = db.execute(
                    "SELECT revision FROM campaigns WHERE scope=? AND partition_id=? "
                    "AND generation=? AND campaign_id=?",
                    (self.scope, partition.key, generation, detail.campaign_id),
                ).fetchone()
                if previous and previous[0] >= detail.snapshot_revision:
                    raise ValueError("Snapshot revision must increase")
                db.execute(
                    "INSERT OR REPLACE INTO campaigns VALUES (?,?,?,?,?,?,?)",
                    (
                        self.scope,
                        partition.key,
                        generation,
                        detail.campaign_id,
                        detail.snapshot_revision,
                        detail.model_dump_json(),
                        sha256(canonical_bytes(detail)),
                    ),
                )

    def list_campaigns(self) -> list[NarrativeCampaignDetail]:
        with self.evidence._lock:
            rows = self.evidence._db.execute(
                "SELECT c.detail_json FROM campaigns c JOIN state_generations s "
                "ON c.scope=s.scope AND c.partition_id=s.partition_id "
                "AND c.generation=s.generation "
                "WHERE c.scope=?",
                (self.scope,),
            ).fetchall()
        return sorted(
            [NarrativeCampaignDetail.model_validate_json(row[0]) for row in rows],
            key=lambda d: (
                d.cti_assessment.cti_score is None,
                -(d.cti_assessment.cti_score or 0),
                d.campaign_id,
            ),
        )

    def get_campaign(self, campaign_id: str) -> NarrativeCampaignDetail:
        for detail in self.list_campaigns():
            if detail.campaign_id == campaign_id:
                return detail
        raise KeyError("Unknown campaign")

    def add_membership(
        self,
        partition: StatePartition,
        generation: int,
        campaign_id: str,
        event_id: str,
        revision: int,
    ) -> None:
        with self.mutation(partition, generation):
            if not self.evidence._db.execute(
                "SELECT 1 FROM active_events WHERE scope=? AND partition_id=? "
                "AND generation=? AND event_id=?",
                (self.scope, partition.key, generation, event_id),
            ).fetchone():
                raise ValueError("Membership event is outside active partition")
            with self.evidence.transaction() as db:
                db.execute(
                    "INSERT OR REPLACE INTO campaign_memberships VALUES (?,?,?,?,?,?,?,?)",
                    (
                        self.scope,
                        partition.key,
                        generation,
                        campaign_id,
                        event_id,
                        datetime.now(UTC).isoformat(),
                        "2.1.0",
                        revision,
                    ),
                )

    def create_job(
        self, partition: StatePartition, generation: int, request: JobRequest
    ) -> JobStatusResponse:
        job_type = {
            ScenarioSwitchRequest: "SCENARIO",
            EventInjectRequest: "INJECT",
            ForensicsVerifyRequest: "FORENSICS",
            ExportRequest: "EXPORT",
        }[type(request)]
        response = JobStatusResponse.model_validate(
            {"job_id": uuid4().hex, "job_type": job_type, "status": "QUEUED"}
        )
        record = JobRecord(
            partition=partition, generation=generation, request=request, response=response
        )
        with self.mutation(partition, generation), self.evidence.transaction() as db:
            db.execute(
                "INSERT INTO jobs VALUES (?,?,?,?,?)",
                (self.scope, response.job_id, partition.key, generation, record.model_dump_json()),
            )
        return response

    def list_job_records(self) -> list[JobRecord]:
        with self.evidence._lock:
            rows = self.evidence._db.execute(
                "SELECT record_json FROM jobs WHERE scope=?", (self.scope,)
            ).fetchall()
        return [JobRecord.model_validate_json(row[0]) for row in rows]

    def get_job_record(self, job_id: str) -> JobRecord:
        for record in self.list_job_records():
            if record.response.job_id == job_id:
                return record
        raise KeyError("Unknown job")

    def get_job(self, job_id: str) -> JobStatusResponse:
        return self.get_job_record(job_id).response

    def update_job(self, response: JobStatusResponse, *, check_generation: bool = True) -> None:
        response = JobStatusResponse.model_validate(response.model_dump())
        record = self.get_job_record(response.job_id)
        with self.evidence._lock:
            if check_generation:
                self.check(record.partition, record.generation)
            updated = record.model_copy(update={"response": response})
            with self.evidence.transaction() as db:
                db.execute(
                    "UPDATE jobs SET record_json=? WHERE scope=? AND job_id=?",
                    (updated.model_dump_json(), self.scope, response.job_id),
                )

    def put_claim_reference(self, reference: ClaimReference) -> None:
        with self.evidence.transaction() as db:
            old = db.execute(
                "SELECT reference_json FROM claim_references WHERE scope=? AND reference_id=?",
                (self.scope, reference.reference_id),
            ).fetchone()
            if old and ClaimReference.model_validate_json(old[0]) != reference:
                raise ValueError("A reference revision needs a new reference ID")
            db.execute(
                "INSERT OR IGNORE INTO claim_references VALUES (?,?,?)",
                (self.scope, reference.reference_id, reference.model_dump_json()),
            )

    def list_claim_references(self) -> list[ClaimReference]:
        with self.evidence._lock:
            rows = self.evidence._db.execute(
                "SELECT reference_json FROM claim_references WHERE scope=?", (self.scope,)
            ).fetchall()
        return [ClaimReference.model_validate_json(row[0]) for row in rows]

    def append_claim_review(
        self, campaign_id: str, assessment: ClaimVerificationAssessment, audit_entry_id: str
    ) -> None:
        if assessment.reviewed_by is None:
            raise ValueError("An authenticated review is required")
        with self.evidence.transaction() as db:
            row = db.execute(
                "SELECT entry_json FROM audit_entries WHERE entry_id=?", (audit_entry_id,)
            ).fetchone()
            if not row or '"action":"CLAIM_REVIEW"' not in row[0]:
                raise ValueError("A retained review audit entry is required")
            db.execute(
                "INSERT INTO claim_reviews VALUES (?,?,?,?,?)",
                (
                    self.scope,
                    uuid4().hex,
                    campaign_id,
                    assessment.model_dump_json(),
                    audit_entry_id,
                ),
            )

    def list_claim_reviews(self, campaign_id: str) -> list[ClaimVerificationAssessment]:
        with self.evidence._lock:
            rows = self.evidence._db.execute(
                "SELECT assessment_json FROM claim_reviews WHERE scope=? "
                "AND campaign_id=? ORDER BY rowid",
                (self.scope, campaign_id),
            ).fetchall()
        return [ClaimVerificationAssessment.model_validate_json(row[0]) for row in rows]

    def put_baseline_bucket(self, partition: StatePartition, bucket: GeoBaselineBucket) -> None:
        if bucket.hour_utc.minute or bucket.hour_utc.second or bucket.hour_utc.microsecond:
            raise ValueError("Baseline bucket must begin at an exact UTC hour")
        with self.evidence.transaction() as db:
            db.execute(
                "INSERT OR REPLACE INTO geo_baseline_buckets VALUES (?,?,?,?,?,?)",
                (
                    self.scope,
                    partition.key,
                    bucket.topic_family_id,
                    bucket.h3_index,
                    bucket.hour_utc.isoformat(),
                    bucket.model_dump_json(),
                ),
            )

    def list_baseline_buckets(self, partition: StatePartition) -> list[GeoBaselineBucket]:
        with self.evidence._lock:
            rows = self.evidence._db.execute(
                "SELECT bucket_json FROM geo_baseline_buckets WHERE scope=? "
                "AND partition_id=? ORDER BY hour_utc",
                (self.scope, partition.key),
            ).fetchall()
        return [GeoBaselineBucket.model_validate_json(row[0]) for row in rows]
