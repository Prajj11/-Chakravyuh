import hashlib
import hmac
from unittest.mock import MagicMock

import pytest

from app.reporting.delivery import AlertDelivery
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import CampaignAlert, CampaignThreatBreakdown


def warning() -> CampaignAlert:
    return CampaignAlert(
        campaign_id="public-campaign",
        assessment=CampaignThreatBreakdown(
            computation_mode="COMPUTED_PIPELINE",
            analysis_status="AVAILABLE",
            parameter_set_id="test",
            coverage_ratio=1,
            evidence_reasons=["test"],
            feature_contributions={"sync": 90},
            cti_score=90,
            threat_level="CRITICAL",
            sync_component=100,
            component_modes={"sync": "COMPUTED_PIPELINE"},
            effective_weights={"sync": 1},
            scored_post_coverage_ratio=1,
            alert_eligible=True,
        ),
    )


def test_outbox_signature_dedup_and_retry(
    repository: EvidenceRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "x" * 32
    delivery = AlertDelivery(repository, "https://alerts.example/receive", secret)
    key = delivery.enqueue(warning(), "2026-10-20T00:00:00Z")
    assert delivery.enqueue(warning(), "2026-10-20T00:00:00Z") == key
    assert delivery.status()["counts"] == {"PENDING": 1}
    opener = MagicMock()
    opener.open.side_effect = OSError("no network")
    monkeypatch.setattr("app.reporting.delivery.build_opener", lambda *_: opener)
    delivery.deliver_one()
    with repository.transaction() as db:
        attempts, status = db.execute("SELECT attempts,status FROM alert_outbox").fetchone()
        assert (attempts, status) == (1, "PENDING")
        db.execute("UPDATE alert_outbox SET next_attempt=0")
    opener.open.side_effect = None
    opener.open.return_value.__enter__.return_value.status = 204
    delivery.deliver_one()
    request = opener.open.call_args.args[0]
    stamp = request.get_header("X-chakravyuh-timestamp")
    expected = hmac.new(
        secret.encode(), stamp.encode() + b"." + request.data, hashlib.sha256
    ).hexdigest()
    assert request.get_header("X-chakravyuh-signature") == expected
    assert request.get_header("Idempotency-key") == key
    assert delivery.status()["counts"] == {"DELIVERED": 1}


def test_disabled_delivery_retains_and_does_not_send(repository: EvidenceRepository) -> None:
    delivery = AlertDelivery(repository, None, None)
    delivery.enqueue(warning(), "2026-10-20T00:00:00Z")
    delivery.deliver_one()
    assert delivery.status() == {"enabled": False, "counts": {"PENDING": 1}}


def test_webhook_requires_https_and_signing_key(repository: EvidenceRepository) -> None:
    with pytest.raises(ValueError):
        AlertDelivery(repository, "http://alerts.example", "x" * 32)
    with pytest.raises(ValueError):
        AlertDelivery(repository, "https://alerts.example", None)
