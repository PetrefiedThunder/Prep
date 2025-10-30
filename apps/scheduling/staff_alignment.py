"""Utilities for reconciling staff availability with booking windows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Sequence

from modules.staff.models import StaffShift


@dataclass(slots=True)
class BookingWindow:
    """Represents a booking that needs to be covered by staff."""

    id: str
    start: datetime
    end: datetime
    required_roles: tuple[str, ...] = ()
    location_id: str | None = None

    def normalize(self) -> None:
        if self.start.tzinfo is None:
            self.start = self.start.replace(tzinfo=timezone.utc)
        else:
            self.start = self.start.astimezone(timezone.utc)
        if self.end.tzinfo is None:
            self.end = self.end.replace(tzinfo=timezone.utc)
        else:
            self.end = self.end.astimezone(timezone.utc)
        if self.end <= self.start:
            raise ValueError("Booking end must be after start")


@dataclass(slots=True)
class StaffAssignment:
    """Assignments between a staff shift and the bookings it covers."""

    shift: StaffShift
    bookings: List[BookingWindow] = field(default_factory=list)

    def add_booking(self, booking: BookingWindow) -> None:
        self.bookings.append(booking)


@dataclass(slots=True)
class StaffAlignmentResult:
    assignments: List[StaffAssignment]
    unfilled_bookings: List[BookingWindow]

    def filled_booking_ids(self) -> List[str]:
        return [booking.id for assignment in self.assignments for booking in assignment.bookings]


def reconcile_staff_availability(
    shifts: Sequence[StaffShift],
    bookings: Sequence[BookingWindow],
) -> StaffAlignmentResult:
    """Return an alignment plan for ``bookings`` based on the provided ``shifts``."""

    normalized_bookings: List[BookingWindow] = []
    for booking in bookings:
        booking.normalize()
        normalized_bookings.append(booking)

    remaining = sorted(normalized_bookings, key=lambda b: (b.start, b.id))
    assignments: List[StaffAssignment] = []

    for shift in sorted(shifts, key=lambda s: (s.start, s.staff_id)):
        applicable: List[BookingWindow] = []
        for booking in list(remaining):
            if not shift.covers(booking.start, booking.end):
                continue
            if booking.location_id and shift.location_id and booking.location_id != shift.location_id:
                continue
            if booking.required_roles:
                if not shift.roles:
                    continue
                if not set(booking.required_roles).intersection(shift.roles):
                    continue
            applicable.append(booking)
            remaining.remove(booking)

        if applicable:
            assignments.append(StaffAssignment(shift=shift, bookings=applicable))

    return StaffAlignmentResult(assignments=assignments, unfilled_bookings=remaining)


__all__ = [
    "BookingWindow",
    "StaffAlignmentResult",
    "StaffAssignment",
    "reconcile_staff_availability",
]
