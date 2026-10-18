from datetime import UTC, datetime, timedelta

import pytest

from app.ingestion.clock import ReplayClock, StaleGeneration


def test_speed_changes_preserve_event_time_and_pause() -> None:
    ticks = [10.0]
    start = datetime(2026, 1, 1, tzinfo=UTC)
    clock = ReplayClock(start, generation=1, speed=2, monotonic=lambda: ticks[0])
    ticks[0] += 5
    assert clock.now() == start + timedelta(seconds=10)
    clock.set_speed(10)
    ticks[0] += 2
    assert clock.now() == start + timedelta(seconds=30)
    clock.pause()
    ticks[0] += 100
    assert clock.now() == start + timedelta(seconds=30)
    clock.resume()
    ticks[0] += 1
    assert clock.now() == start + timedelta(seconds=40)


def test_reset_cancels_old_generation_and_bounds_at_last_event() -> None:
    ticks = [0.0]
    start = datetime(2026, 1, 1, tzinfo=UTC)
    clock = ReplayClock(start, generation=1, monotonic=lambda: ticks[0])
    assert clock.delay_until(start + timedelta(seconds=60), generation=1) == 60
    clock.reset(start, generation=2, speed=100, end=start + timedelta(seconds=180))
    with pytest.raises(StaleGeneration):
        clock.delay_until(start, generation=1)
    ticks[0] = 10
    assert clock.now() == start + timedelta(seconds=180)
    assert clock.delay_until(start, generation=2) == 0
    with pytest.raises(ValueError):
        clock.set_speed(0)
    with pytest.raises(ValueError):
        clock.reset(start, generation=2)


def test_clock_rejects_naive_time_and_invalid_speeds() -> None:
    with pytest.raises(ValueError):
        ReplayClock(datetime(2026, 1, 1), generation=0)
    for speed in (float("nan"), float("inf"), -1, 101):
        with pytest.raises(ValueError):
            ReplayClock(datetime(2026, 1, 1, tzinfo=UTC), generation=0, speed=speed)
