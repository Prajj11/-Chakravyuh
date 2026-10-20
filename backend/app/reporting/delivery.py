"""Durable, opt-in HTTPS alert delivery with bounded retries and idempotency keys."""

import asyncio
import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from app.evidence.canonical import canonical_bytes, sha256
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import CampaignAlert


class AlertDelivery:
    def __init__(self, repository: EvidenceRepository, url: str | None, secret: str | None) -> None:
        self.repo, self.url, self.secret = repository, url, secret
        if url:
            parsed = urlsplit(url)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.fragment
            ):
                raise ValueError("Alert webhook must be an HTTPS URL without user info or fragment")
            if not secret or len(secret) < 32:
                raise ValueError("Webhook signing secret must contain at least 32 characters")
        with repository.transaction() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS alert_outbox (id TEXT PRIMARY KEY, body BLOB, "
                "attempts INTEGER DEFAULT 0, next_attempt REAL DEFAULT 0, "
                "status TEXT DEFAULT 'PENDING', error TEXT)"
            )
        self.task: asyncio.Task[None] | None = None
        self.stopping = asyncio.Event()

    def enqueue(self, alert: CampaignAlert, observation_time: str) -> str:
        # No account handles or post text are sent. Synthetic alerts never call this path.
        body = canonical_bytes(
            {
                "kind": "PUBLIC_CAMPAIGN_WARNING",
                "campaign_id": alert.campaign_id,
                "observation_time": observation_time,
                "assessment": alert.assessment,
            }
        )
        key = sha256(body)
        with self.repo.transaction() as db:
            db.execute("INSERT OR IGNORE INTO alert_outbox(id,body) VALUES (?,?)", (key, body))
        return key

    def status(self) -> dict[str, Any]:
        with self.repo._lock:
            rows = self.repo._db.execute(
                "SELECT status,COUNT(*) FROM alert_outbox GROUP BY status"
            ).fetchall()
        return {"enabled": bool(self.url), "counts": dict(rows)}

    def start(self) -> None:
        if self.url:
            self.task = asyncio.create_task(self.run())

    async def close(self) -> None:
        if self.task:
            self.stopping.set()
            await self.task

    async def run(self) -> None:
        while not self.stopping.is_set():
            await asyncio.to_thread(self.deliver_one)
            try:
                await asyncio.wait_for(self.stopping.wait(), timeout=5)
            except TimeoutError:
                pass

    def deliver_one(self) -> None:
        if not self.url:
            return
        from app.ingestion.live import NoRedirect

        with self.repo._lock:
            row = self.repo._db.execute(
                "SELECT id,body,attempts FROM alert_outbox "
                "WHERE status='PENDING' AND next_attempt<=? ORDER BY next_attempt LIMIT 1",
                (time.time(),),
            ).fetchone()
        if row is None:
            return
        key, body, attempts = row
        stamp = str(int(time.time()))
        signature = hmac.new(
            (self.secret or "").encode(), stamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        error = None
        status = "DELIVERED"
        try:
            request = Request(
                self.url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Idempotency-Key": key,
                    "X-Chakravyuh-Timestamp": stamp,
                    "X-Chakravyuh-Signature": signature,
                },
                method="POST",
            )
            with build_opener(NoRedirect).open(request, timeout=15) as response:
                if not 200 <= response.status < 300:
                    raise ValueError("Webhook did not acknowledge delivery")
        except Exception as exc:
            error = type(exc).__name__
            status = "FAILED" if attempts + 1 >= 8 else "PENDING"
        with self.repo.transaction() as db:
            db.execute(
                "UPDATE alert_outbox SET status=?,attempts=?,next_attempt=?,error=? WHERE id=?",
                (status, attempts + 1, time.time() + min(30 * 2**attempts, 3600), error, key),
            )
