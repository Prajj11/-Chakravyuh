from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.config import Parameters
from app.ingestion.contracts import SourceEvent
from app.repositories.evidence import EvidenceRepository
from app.schemas.models import AccountProfile, DataOrigin, PlatformType


def pytest_configure(config: pytest.Config) -> None:
    # Windows Store Python may not have access to the shared system pytest temp directory.
    if config.option.basetemp is None:
        parent = Path(__file__).resolve().parents[2] / ".runtime" / "test-tmp"
        parent.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(parent / uuid4().hex)


@pytest.fixture
def repository(tmp_path: Path) -> Iterator[EvidenceRepository]:
    repo = EvidenceRepository(tmp_path, Parameters())
    yield repo
    repo.close()


@pytest.fixture
def source() -> SourceEvent:
    return SourceEvent(
        source_event_key="post-1",
        platform=PlatformType.SIMULATOR,
        data_origin=DataOrigin.USER_INJECTED,
        collector_id="test-collector",
        collector_scope="test-scope",
        timestamp_utc=datetime(2026, 10, 18, tzinfo=UTC),
        account=AccountProfile(account_id="simulator:author", handle="@author"),
        text="Exact text: नमस्ते  e\u0301",
        hashtags=("#original",),
    )
