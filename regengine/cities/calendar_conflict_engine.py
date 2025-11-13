"""
Calendar Conflict Engine

Checks booking requests against inspections, maintenance windows,
blackouts, and seasonal restrictions to prevent scheduling conflicts.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass
class ConflictWindow:
    """A time window that blocks bookings."""

    type: str  # 'inspection', 'maintenance', 'blackout', 'seasonal', 'existing_booking'
    starts_at: datetime
    ends_at: datetime
    reason: str
    reference_id: str | None = None
    allow_override: bool = False


class ConflictCheckResult:
    """Result of conflict check."""

    def __init__(self):
        self.has_conflicts: bool = False
        self.conflicts: list[ConflictWindow] = []
        self.checked_at: datetime = datetime.now(UTC)

    def add_conflict(self, conflict: ConflictWindow):
        """Add a conflict."""
        self.conflicts.append(conflict)
        self.has_conflicts = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_conflicts": self.has_conflicts,
            "conflicts": [
                {
                    "type": c.type,
                    "starts_at": c.starts_at.isoformat(),
                    "ends_at": c.ends_at.isoformat(),
                    "reason": c.reason,
                    "reference_id": c.reference_id,
                    "allow_override": c.allow_override,
                }
                for c in self.conflicts
            ],
            "checked_at": self.checked_at.isoformat(),
        }


class CalendarConflictEngine:
    """
    Calendar conflict detection engine.

    Checks booking requests against:
    - Existing bookings
    - Scheduled inspections (with buffers)
    - Maintenance windows
    - Blackout dates
    - Seasonal restrictions
    - Jurisdiction closures

    Usage:
        engine = CalendarConflictEngine()
        result = engine.check_conflicts(
            kitchen_id="...",
            requested_start=datetime(...),
            requested_end=datetime(...),
            inspection_buffer_hours=4,
            existing_bookings=[...],
            inspections=[...],
            maintenance_windows=[...],
            blackouts=[...],
            seasonal_restrictions=[...]
        )
    """

    def check_conflicts(
        self,
        kitchen_id: str,
        requested_start: datetime,
        requested_end: datetime,
        inspection_buffer_hours: int = 4,
        existing_bookings: list[dict[str, Any]] | None = None,
        inspections: list[dict[str, Any]] | None = None,
        maintenance_windows: list[dict[str, Any]] | None = None,
        blackouts: list[dict[str, Any]] | None = None,
        seasonal_restrictions: list[dict[str, Any]] | None = None,
    ) -> ConflictCheckResult:
        """
        Check for all calendar conflicts.

        Args:
            kitchen_id: Kitchen identifier
            requested_start: Requested booking start
            requested_end: Requested booking end
            inspection_buffer_hours: Hours before/after inspection to block
            existing_bookings: List of existing bookings
            inspections: List of scheduled inspections
            maintenance_windows: List of maintenance windows
            blackouts: List of blackout periods
            seasonal_restrictions: List of seasonal restrictions

        Returns:
            ConflictCheckResult with any conflicts found
        """
        result = ConflictCheckResult()

        # Check existing bookings
        if existing_bookings:
            self._check_existing_bookings(requested_start, requested_end, existing_bookings, result)

        # Check inspections (with buffer)
        if inspections:
            self._check_inspections(
                requested_start, requested_end, inspections, inspection_buffer_hours, result
            )

        # Check maintenance windows
        if maintenance_windows:
            self._check_maintenance_windows(
                requested_start, requested_end, maintenance_windows, result
            )

        # Check blackouts
        if blackouts:
            self._check_blackouts(requested_start, requested_end, blackouts, result)

        # Check seasonal restrictions
        if seasonal_restrictions:
            self._check_seasonal_restrictions(
                requested_start, requested_end, seasonal_restrictions, result
            )

        return result

    def _check_existing_bookings(
        self,
        requested_start: datetime,
        requested_end: datetime,
        bookings: list[dict[str, Any]],
        result: ConflictCheckResult,
    ):
        """Check for overlapping existing bookings."""
        for booking in bookings:
            booking_start = datetime.fromisoformat(booking["starts_at"])
            booking_end = datetime.fromisoformat(booking["ends_at"])

            if self._overlaps(requested_start, requested_end, booking_start, booking_end):
                result.add_conflict(
                    ConflictWindow(
                        type="existing_booking",
                        starts_at=booking_start,
                        ends_at=booking_end,
                        reason=f"Existing booking by {booking.get('maker_name', 'another user')}",
                        reference_id=booking.get("id"),
                    )
                )

    def _check_inspections(
        self,
        requested_start: datetime,
        requested_end: datetime,
        inspections: list[dict[str, Any]],
        buffer_hours: int,
        result: ConflictCheckResult,
    ):
        """Check for inspection conflicts (with buffer)."""
        for inspection in inspections:
            if inspection.get("status") not in ["scheduled", "pending"]:
                continue

            inspection_time = datetime.fromisoformat(inspection["scheduled_for"])

            # Apply buffer before and after
            buffer_start = inspection_time - timedelta(hours=buffer_hours)
            buffer_end = inspection_time + timedelta(hours=buffer_hours)

            if self._overlaps(requested_start, requested_end, buffer_start, buffer_end):
                inspection_type = inspection.get("inspection_type_code", "inspection")
                result.add_conflict(
                    ConflictWindow(
                        type="inspection",
                        starts_at=buffer_start,
                        ends_at=buffer_end,
                        reason=f"{inspection_type.title()} inspection scheduled with {buffer_hours}h buffer",
                        reference_id=inspection.get("id"),
                    )
                )

    def _check_maintenance_windows(
        self,
        requested_start: datetime,
        requested_end: datetime,
        windows: list[dict[str, Any]],
        result: ConflictCheckResult,
    ):
        """Check for maintenance window conflicts."""
        for window in windows:
            window_start = datetime.fromisoformat(window["starts_at"])
            window_end = datetime.fromisoformat(window["ends_at"])

            if self._overlaps(requested_start, requested_end, window_start, window_end):
                result.add_conflict(
                    ConflictWindow(
                        type="maintenance",
                        starts_at=window_start,
                        ends_at=window_end,
                        reason=window.get("reason", "Scheduled maintenance"),
                        reference_id=window.get("id"),
                    )
                )

    def _check_blackouts(
        self,
        requested_start: datetime,
        requested_end: datetime,
        blackouts: list[dict[str, Any]],
        result: ConflictCheckResult,
    ):
        """Check for blackout period conflicts."""
        for blackout in blackouts:
            blackout_start = datetime.fromisoformat(blackout["starts_at"])
            blackout_end = datetime.fromisoformat(blackout["ends_at"])

            if self._overlaps(requested_start, requested_end, blackout_start, blackout_end):
                result.add_conflict(
                    ConflictWindow(
                        type="blackout",
                        starts_at=blackout_start,
                        ends_at=blackout_end,
                        reason=blackout.get("reason", "Blackout period"),
                        reference_id=blackout.get("id"),
                        allow_override=blackout.get("allow_override", False),
                    )
                )

    def _check_seasonal_restrictions(
        self,
        requested_start: datetime,
        requested_end: datetime,
        restrictions: list[dict[str, Any]],
        result: ConflictCheckResult,
    ):
        """Check for seasonal restriction conflicts."""
        for restriction in restrictions:
            # Seasonal restrictions use dates, not datetimes
            starts_on = restriction["starts_on"]  # DATE
            ends_on = restriction["ends_on"]  # DATE

            # Convert to datetime for comparison
            # (Simplified - would need to handle annual recurrence properly)
            restriction_start = parse_datetime_safe(f"{starts_on}T00:00:00")
            restriction_end = parse_datetime_safe(f"{ends_on}T23:59:59")

            if self._overlaps(requested_start, requested_end, restriction_start, restriction_end):
                restriction_type = restriction.get("restriction_type", "prohibited")
                if restriction_type == "prohibited":
                    result.add_conflict(
                        ConflictWindow(
                            type="seasonal",
                            starts_at=restriction_start,
                            ends_at=restriction_end,
                            reason=restriction.get("reason", "Seasonal restriction"),
                            reference_id=restriction.get("id"),
                        )
                    )

    def _overlaps(self, start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
        """Check if two time ranges overlap."""
        return start1 < end2 and end1 > start2

    def get_available_slots(
        self,
        kitchen_id: str,
        date: datetime,
        duration_hours: int,
        existing_bookings: list[dict[str, Any]] | None = None,
        inspections: list[dict[str, Any]] | None = None,
        maintenance_windows: list[dict[str, Any]] | None = None,
        blackouts: list[dict[str, Any]] | None = None,
        operating_hours_start: int = 6,  # 6 AM
        operating_hours_end: int = 22,  # 10 PM
    ) -> list[dict[str, Any]]:
        """
        Find available time slots on a given date.

        Args:
            kitchen_id: Kitchen identifier
            date: Date to check
            duration_hours: Desired booking duration
            existing_bookings: List of existing bookings
            inspections: List of scheduled inspections
            maintenance_windows: List of maintenance windows
            blackouts: List of blackout periods
            operating_hours_start: Start of operating hours (24h format)
            operating_hours_end: End of operating hours (24h format)

        Returns:
            List of available time slots with start/end times
        """
        available_slots = []

        # Generate candidate slots (every hour within operating hours)
        day_start = date.replace(hour=operating_hours_start, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=operating_hours_end, minute=0, second=0, microsecond=0)

        current_time = day_start
        while current_time + timedelta(hours=duration_hours) <= day_end:
            slot_end = current_time + timedelta(hours=duration_hours)

            # Check if this slot has conflicts
            conflict_result = self.check_conflicts(
                kitchen_id=kitchen_id,
                requested_start=current_time,
                requested_end=slot_end,
                existing_bookings=existing_bookings,
                inspections=inspections,
                maintenance_windows=maintenance_windows,
                blackouts=blackouts,
            )

            if not conflict_result.has_conflicts:
                available_slots.append(
                    {
                        "start": current_time.isoformat(),
                        "end": slot_end.isoformat(),
                        "duration_hours": duration_hours,
                    }
                )

            # Move to next hour
            current_time += timedelta(hours=1)

        return available_slots


# Example usage
if __name__ == "__main__":
    engine = CalendarConflictEngine()

    # Example: Check for conflicts
    result = engine.check_conflicts(
        kitchen_id="kitchen-123",
        requested_start=datetime(2025, 11, 15, 10, 0),
        requested_end=datetime(2025, 11, 15, 18, 0),
        inspection_buffer_hours=4,
        existing_bookings=[
            {
                "id": "booking-1",
                "starts_at": "2025-11-15T15:00:00",
                "ends_at": "2025-11-15T20:00:00",
                "maker_name": "Alice",
            }
        ],
        inspections=[
            {
                "id": "inspection-1",
                "scheduled_for": "2025-11-15T09:00:00",
                "status": "scheduled",
                "inspection_type_code": "health",
            }
        ],
    )

    print(f"Has conflicts: {result.has_conflicts}")
    print(f"Number of conflicts: {len(result.conflicts)}")

    for conflict in result.conflicts:
        print(f"\n{conflict.type.upper()}: {conflict.reason}")
        print(f"  {conflict.starts_at} - {conflict.ends_at}")

    # Example: Find available slots
    available = engine.get_available_slots(
        kitchen_id="kitchen-123",
        date=datetime(2025, 11, 16),
        duration_hours=4,
        existing_bookings=[],
        inspections=[],
    )

    print(f"\nAvailable {len(available)} slots on 2025-11-16:")
    for slot in available[:5]:  # Show first 5
        print(f"  {slot['start']} - {slot['end']}")
