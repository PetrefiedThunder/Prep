"""Simplified booking repository used by the space optimizer pipeline.

The real Prep stack exposes bookings via SQLAlchemy models and service layers.
For testability inside this kata we model a lightweight in-memory repository
that surfaces a representative subset of booking metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Sequence


@dataclass(frozen=True, slots=True)
class Booking:
    """Immutable booking record sourced from historical transactions."""

    booking_id: str
    kitchen_id: str
    start: datetime
    end: datetime
    status: str = "completed"

    def __post_init__(self) -> None:
        if self.end <= self.start:
            msg = (
                "Booking end must be after start: "
                f"{self.booking_id} ({self.start.isoformat()} -> {self.end.isoformat()})"
            )
            raise ValueError(msg)
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Booking timestamps must be timezone-aware")


def _utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


_DEFAULT_BOOKINGS: Sequence[Booking] = (
    Booking(
        booking_id="bk-1001",
        kitchen_id="kitchen-1",
        start=_utc(2024, 1, 1, 9),
        end=_utc(2024, 1, 1, 12),
    ),
    Booking(
        booking_id="bk-1002",
        kitchen_id="kitchen-1",
        start=_utc(2024, 1, 1, 15),
        end=_utc(2024, 1, 1, 17),
    ),
    Booking(
        booking_id="bk-1003",
        kitchen_id="kitchen-1",
        start=_utc(2024, 1, 2, 9),
        end=_utc(2024, 1, 2, 11),
    ),
    Booking(
        booking_id="bk-2001",
        kitchen_id="kitchen-2",
        start=_utc(2024, 1, 3, 10),
        end=_utc(2024, 1, 3, 13),
    ),
    Booking(
        booking_id="bk-2002",
        kitchen_id="kitchen-2",
        start=_utc(2024, 1, 3, 14),
        end=_utc(2024, 1, 3, 15, 30),
    ),
    Booking(
        booking_id="bk-2003",
        kitchen_id="kitchen-2",
        start=_utc(2024, 1, 3, 20),
        end=_utc(2024, 1, 3, 22),
    ),
)


class BookingHistoryRepository:
    """Read-only repository exposing historical bookings for analytics tasks."""

    def __init__(self, source: Iterable[Booking] | None = None) -> None:
        self._bookings: List[Booking] = list(source or _DEFAULT_BOOKINGS)

    def list_completed_bookings(self) -> List[Booking]:
        """Return bookings that finished successfully, ordered chronologically."""

        completed = [b for b in self._bookings if b.status.lower() == "completed"]
        return sorted(completed, key=lambda booking: (booking.kitchen_id, booking.start))

    def latest_booking_before(self, kitchen_id: str, reference: datetime) -> Booking | None:
        """Find the most recent completed booking ending before ``reference``."""

        relevant = (
            booking
            for booking in self._bookings
            if booking.kitchen_id == kitchen_id
            and booking.status.lower() == "completed"
            and booking.end <= reference
        )
        return max(relevant, default=None, key=lambda booking: booking.end)


__all__ = ["Booking", "BookingHistoryRepository"]
