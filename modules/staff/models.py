"""Data models for staffing integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass(slots=True)
class StaffMember:
    """Represents a staff member sourced from an external staffing provider."""

    id: str
    external_id: str
    source: str
    name: str
    email: str | None = None
    phone: str | None = None
    roles: tuple[str, ...] = ()

    def primary_role(self) -> str | None:
        return self.roles[0] if self.roles else None


@dataclass(slots=True)
class StaffShift:
    """Represents a scheduled shift for a staff member."""

    id: str
    external_id: str
    staff_id: str
    source: str
    start: datetime
    end: datetime
    location_id: str | None = None
    roles: tuple[str, ...] = ()
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.start.tzinfo is None:
            self.start = self.start.replace(tzinfo=timezone.utc)
        else:
            self.start = self.start.astimezone(timezone.utc)

        if self.end.tzinfo is None:
            self.end = self.end.replace(tzinfo=timezone.utc)
        else:
            self.end = self.end.astimezone(timezone.utc)

        if self.end <= self.start:
            raise ValueError("Shift end must be after start")

    def duration_hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600

    def covers(self, start: datetime, end: datetime) -> bool:
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        else:
            start = start.astimezone(timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        else:
            end = end.astimezone(timezone.utc)
        return self.start <= start and self.end >= end

    def overlaps(self, start: datetime, end: datetime) -> bool:
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        else:
            start = start.astimezone(timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        else:
            end = end.astimezone(timezone.utc)
        return self.start < end and self.end > start


@dataclass(slots=True)
class StaffingSnapshot:
    """Snapshot of staff and their shifts for a given sync window."""

    staff: Dict[str, StaffMember]
    shifts: List[StaffShift]

    def staff_list(self) -> List[StaffMember]:
        return list(self.staff.values())

    def shifts_for_staff(self, staff_id: str) -> List[StaffShift]:
        return [shift for shift in self.shifts if shift.staff_id == staff_id]

    def shifts_by_location(self, location_id: str | None) -> List[StaffShift]:
        return [shift for shift in self.shifts if shift.location_id == location_id]


__all__ = ["StaffMember", "StaffShift", "StaffingSnapshot"]
