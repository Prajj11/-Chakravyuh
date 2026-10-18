"""Monotonic wall-time pacing with a separate, generation-scoped event-time clock."""

import math
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from threading import RLock


class StaleGeneration(RuntimeError):
    """An old replay worker attempted to publish after its generation ended."""


class ReplayClock:
    def __init__(
        self,
        start: datetime,
        *,
        generation: int,
        speed: float = 1,
        end: datetime | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._lock = RLock()
        self._monotonic = monotonic
        self.generation = generation - 1
        self.reset(start, generation=generation, speed=speed, end=end)

    @staticmethod
    def _validate(start: datetime, speed: float, end: datetime | None) -> None:
        if start.tzinfo is None or start.utcoffset() is None:
            raise ValueError("Event time must be timezone-aware")
        if not math.isfinite(speed) or not 0 < speed <= 100:
            raise ValueError("Replay speed must be greater than zero and at most 100")
        if end is not None and (end.tzinfo is None or end < start):
            raise ValueError("Replay end must be aware and no earlier than its start")

    def reset(
        self,
        start: datetime,
        *,
        generation: int,
        speed: float = 1,
        end: datetime | None = None,
    ) -> None:
        self._validate(start, speed, end)
        with self._lock:
            if generation <= self.generation:
                raise ValueError("A reset requires a newer generation")
            self.generation = generation
            self._anchor = start.astimezone(UTC)
            self._end = end.astimezone(UTC) if end else None
            self._wall_anchor = self._monotonic()
            self._speed = speed
            self._paused = False

    def now(self) -> datetime:
        with self._lock:
            elapsed = 0.0 if self._paused else max(0, self._monotonic() - self._wall_anchor)
            cursor = self._anchor + timedelta(seconds=elapsed * self._speed)
            return min(cursor, self._end) if self._end is not None else cursor

    def set_speed(self, speed: float) -> None:
        with self._lock:
            self._validate(self._anchor, speed, self._end)
            self._anchor = self.now()
            self._wall_anchor = self._monotonic()
            self._speed = speed

    def pause(self) -> None:
        with self._lock:
            self._anchor = self.now()
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._wall_anchor = self._monotonic()
            self._paused = False

    def check_generation(self, generation: int) -> None:
        with self._lock:
            if generation != self.generation:
                raise StaleGeneration("Replay generation has been reset")

    def delay_until(self, timestamp: datetime, *, generation: int) -> float:
        """Return seconds for the async scheduler; never sleep in a scoring worker."""
        with self._lock:
            self.check_generation(generation)
            if timestamp.tzinfo is None:
                raise ValueError("Event time must be timezone-aware")
            return max(0, (timestamp - self.now()).total_seconds() / self._speed)
