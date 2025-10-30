"""Simplified delivery log repository for the space optimizer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Sequence


@dataclass(frozen=True, slots=True)
class DeliveryLog:
    """Snapshot of a logistics event tied to a kitchen."""

    log_id: str
    booking_id: str
    kitchen_id: str
    completed_at: datetime
    duration_minutes: int
    status: str = "completed"

    def __post_init__(self) -> None:
        if self.duration_minutes <= 0:
            raise ValueError("Delivery duration must be positive")
        if self.completed_at.tzinfo is None:
            raise ValueError("Delivery timestamps must be timezone-aware")


def _utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


_DEFAULT_DELIVERIES: Sequence[DeliveryLog] = (
    DeliveryLog(
        log_id="dl-5001",
        booking_id="bk-1001",
        kitchen_id="kitchen-1",
        completed_at=_utc(2024, 1, 1, 13),
        duration_minutes=30,
    ),
    DeliveryLog(
        log_id="dl-5002",
        booking_id="bk-1001",
        kitchen_id="kitchen-1",
        completed_at=_utc(2024, 1, 1, 14),
        duration_minutes=20,
    ),
    DeliveryLog(
        log_id="dl-5003",
        booking_id="bk-1002",
        kitchen_id="kitchen-1",
        completed_at=_utc(2024, 1, 1, 18, 30),
        duration_minutes=40,
    ),
    DeliveryLog(
        log_id="dl-5004",
        booking_id="bk-1002",
        kitchen_id="kitchen-1",
        completed_at=_utc(2024, 1, 2, 12, 30),
        duration_minutes=35,
    ),
    DeliveryLog(
        log_id="dl-6001",
        booking_id="bk-2001",
        kitchen_id="kitchen-2",
        completed_at=_utc(2024, 1, 3, 13, 20),
        duration_minutes=15,
    ),
    DeliveryLog(
        log_id="dl-6002",
        booking_id="bk-9999",
        kitchen_id="kitchen-2",
        completed_at=_utc(2024, 1, 4, 9),
        duration_minutes=25,
        status="cancelled",
    ),
)


class DeliveryLogRepository:
    """Provides historical delivery metrics for analytics pipelines."""

    def __init__(self, source: Iterable[DeliveryLog] | None = None) -> None:
        self._logs: List[DeliveryLog] = list(source or _DEFAULT_DELIVERIES)

    def list_completed_deliveries(self) -> List[DeliveryLog]:
        """Return completed deliveries ordered chronologically by completion time."""

        completed = [log for log in self._logs if log.status.lower() == "completed"]
        return sorted(completed, key=lambda log: (log.kitchen_id, log.completed_at))

    def deliveries_for_kitchen(self, kitchen_id: str) -> List[DeliveryLog]:
        """Return chronologically ordered deliveries for the given kitchen."""

        deliveries = [log for log in self.list_completed_deliveries() if log.kitchen_id == kitchen_id]
        return sorted(deliveries, key=lambda log: log.completed_at)


__all__ = ["DeliveryLog", "DeliveryLogRepository"]
