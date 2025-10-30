"""Domain service for managing prep-time driven availability windows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Iterable, List

from integrations.square.webhooks import PrepTimeUpdate


@dataclass
class AvailabilityWindow:
    """A concrete availability window derived from prep-time updates."""

    start_at: datetime
    end_at: datetime
    order_id: str

    def expand(self, other: "AvailabilityWindow") -> None:
        """Merge another window into this one if they overlap."""

        if other.start_at < self.start_at:
            self.start_at = other.start_at
        if other.end_at > self.end_at:
            self.end_at = other.end_at
        self.order_id = other.order_id


@dataclass
class KitchenSchedule:
    """Tracks dynamic availability for a single kitchen/location."""

    location_id: str
    windows: List[AvailabilityWindow] = field(default_factory=list)
    latest_prep_time_seconds: int = 0


class SchedulingService:
    """Service responsible for reacting to prep-time updates."""

    def __init__(self) -> None:
        self._schedules: Dict[str, KitchenSchedule] = {}

    def ingest_prep_time_update(self, update: PrepTimeUpdate) -> AvailabilityWindow:
        """Record a Square prep-time update and recalculate availability."""

        schedule = self._schedules.setdefault(
            update.location_id, KitchenSchedule(location_id=update.location_id)
        )

        schedule.latest_prep_time_seconds = update.prep_time_seconds

        new_window = AvailabilityWindow(
            start_at=update.ready_at - timedelta(seconds=update.prep_time_seconds),
            end_at=update.ready_at,
            order_id=update.order_id,
        )

        schedule.windows = [
            window for window in schedule.windows if window.order_id != update.order_id
        ]
        schedule.windows.append(new_window)
        schedule.windows = self._merge(schedule.windows)
        return new_window

    def windows_for(self, location_id: str) -> List[AvailabilityWindow]:
        """Return the current availability windows for the provided location."""

        schedule = self._schedules.get(location_id)
        if not schedule:
            return []
        return list(schedule.windows)

    def _merge(self, windows: Iterable[AvailabilityWindow]) -> List[AvailabilityWindow]:
        sorted_windows = sorted(windows, key=lambda window: window.start_at)
        merged: List[AvailabilityWindow] = []

        for window in sorted_windows:
            if not merged:
                merged.append(window)
                continue

            last = merged[-1]
            if window.start_at <= last.end_at:
                last.expand(window)
            else:
                merged.append(window)

        return merged


__all__ = ["AvailabilityWindow", "SchedulingService"]
