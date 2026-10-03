"""Watering detection and next-watering estimate, from soil moisture readings.

Pure logic with timestamps in seconds, so it can be tested without Home
Assistant and persisted as plain JSON.
"""

from __future__ import annotations

# A rise of this many points over the recent minimum is a watering.
WATERING_RISE = 15
# The recent minimum is taken over this window.
BASELINE_WINDOW = 3 * 3600
# Readings closer than this replace each other, to bound the history size.
MIN_SPACING = 15 * 60
HISTORY = 7 * 24 * 3600
# Water spreads through the soil for a while after watering: ignored for the rate.
SOAK_TIME = 2 * 3600
MIN_RATE_SPAN = 6 * 3600
MIN_RATE_POINTS = 3
# Below this drying speed (points per hour) no estimate is given.
MIN_DRYING_RATE = 0.05
MAX_ESTIMATE = 60 * 24 * 3600
# A lone reading this far from both neighbours, which agree, is a glitch.
SPIKE = 15
SPIKE_NEIGHBOURS = 5


def _without_spikes(readings: list[tuple[float, float]]) -> list[tuple[float, float]]:
    kept = []
    for index, (time, value) in enumerate(readings):
        if 0 < index < len(readings) - 1:
            previous, following = readings[index - 1][1], readings[index + 1][1]
            if (
                abs(previous - following) < SPIKE_NEIGHBOURS
                and abs(value - previous) >= SPIKE
                and abs(value - following) >= SPIKE
            ):
                continue
        kept.append((time, value))
    return kept


class WateringTracker:
    """Follows one plant's moisture to date its waterings and the next one."""

    def __init__(
        self,
        readings: list[tuple[float, float]] | None = None,
        last_watered: float | None = None,
    ) -> None:
        self.readings = sorted(readings or [])
        self.last_watered = last_watered
        # A rise waits for the next reading before it counts as a watering.
        self._pending: tuple[float, float] | None = None

    @classmethod
    def from_dict(cls, data: dict | None) -> WateringTracker:
        data = data or {}
        readings = [
            (float(t), float(v))
            for t, v in data.get("readings", [])
            if isinstance(t, (int, float)) and isinstance(v, (int, float))
        ]
        last = data.get("last_watered")
        return cls(readings, float(last) if isinstance(last, (int, float)) else None)

    def as_dict(self) -> dict:
        return {
            "readings": [[round(t, 1), v] for t, v in self.readings],
            "last_watered": self.last_watered,
        }

    def add(self, time: float, value: float) -> bool:
        """Record a valid reading; return True when it confirms a watering."""
        if self.readings and time < self.readings[-1][0]:
            return False
        watered = False
        if self._pending is not None:
            pending_time, baseline = self._pending
            self._pending = None
            if value >= baseline + WATERING_RISE:
                self.last_watered = pending_time
                watered = True
        else:
            recent = [v for t, v in self.readings if time - BASELINE_WINDOW <= t < time]
            just_watered = (
                self.last_watered is not None and time - self.last_watered < BASELINE_WINDOW
            )
            if recent and not just_watered and value >= min(recent) + WATERING_RISE:
                self._pending = (time, min(recent))

        if self.readings and time - self.readings[-1][0] < MIN_SPACING and not watered:
            self.readings[-1] = (time, value)
        else:
            self.readings.append((time, value))
        self.readings = [(t, v) for t, v in self.readings if t >= time - HISTORY]
        return watered

    def mark_watered(self, time: float) -> None:
        """Record a watering reported by the user."""
        self.last_watered = time
        self._pending = None

    def drying_rate(self, now: float) -> float | None:
        """Points of moisture lost per hour since the last watering, if drying."""
        start = now - HISTORY
        if self.last_watered is not None:
            start = max(start, self.last_watered + SOAK_TIME)
        points = _without_spikes([(t, v) for t, v in self.readings if t >= start])
        if len(points) < MIN_RATE_POINTS or points[-1][0] - points[0][0] < MIN_RATE_SPAN:
            return None
        hours = [t / 3600 for t, _ in points]
        values = [v for _, v in points]
        mean_h = sum(hours) / len(hours)
        mean_v = sum(values) / len(values)
        spread = sum((h - mean_h) ** 2 for h in hours)
        slope = sum((h - mean_h) * (v - mean_v) for h, v in zip(hours, values)) / spread
        return -slope if -slope >= MIN_DRYING_RATE else None

    def next_watering(self, now: float, current: float | None, low: float) -> float | None:
        """Estimated time the moisture reaches the watering threshold."""
        if current is None:
            return None
        if current <= low:
            return now
        rate = self.drying_rate(now)
        if rate is None:
            return None
        seconds = (current - low) / rate * 3600
        return now + seconds if seconds <= MAX_ESTIMATE else None
