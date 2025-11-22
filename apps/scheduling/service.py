"""In-memory scheduling service for handling prep-time updates."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from integrations.square.webhooks import PrepTimeUpdate


@dataclass
class PrepTimeWindow:
    """Represents a prep window for a location."""

    location_id: str
    order_id: str
    start_at: datetime
    end_at: datetime
    updated_at: datetime


class SchedulingService:
    """Aggregate prep-time updates into consolidated availability windows."""

    def __init__(self) -> None:
        self._windows: defaultdict[str, list[PrepTimeWindow]] = defaultdict(list)

    def ingest_prep_time_update(self, update: PrepTimeUpdate) -> PrepTimeWindow:
        start_at = update.ready_at - timedelta(seconds=update.prep_time_seconds)
        new_window = PrepTimeWindow(
            location_id=update.location_id,
            order_id=update.order_id,
            start_at=start_at,
            end_at=update.ready_at,
            updated_at=update.updated_at,
        )

        windows = self._windows[update.location_id]
        merged_indices: list[int] = []

        for idx, window in enumerate(windows):
            # Check for overlap between the new window and existing windows.
            if new_window.end_at <= window.start_at or new_window.start_at >= window.end_at:
                continue

            new_window.start_at = min(new_window.start_at, window.start_at)
            new_window.end_at = max(new_window.end_at, window.end_at)

            if window.updated_at > new_window.updated_at:
                new_window.order_id = window.order_id
                new_window.updated_at = window.updated_at

            merged_indices.append(idx)

        for idx in reversed(merged_indices):
            windows.pop(idx)

        windows.append(new_window)
        windows.sort(key=lambda w: w.start_at)
        return new_window

    def windows_for(self, location_id: str) -> list[PrepTimeWindow]:
        """Return the current windows for the given location."""

        return list(self._windows.get(location_id, []))
