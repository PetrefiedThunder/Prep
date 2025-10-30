"""Sync job for consolidating staffing data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Sequence, Tuple

from apps.scheduling.staff_alignment import (
    BookingWindow,
    StaffAlignmentResult,
    reconcile_staff_availability,
)
from integrations.staffing.deputy import DeputyClient
from integrations.staffing.seven_shifts import SevenShiftsClient
from modules.staff.models import StaffMember, StaffShift, StaffingSnapshot


@dataclass(slots=True)
class StaffingSyncResult:
    """Result of executing a staffing synchronization job."""

    snapshot: StaffingSnapshot
    alignment: StaffAlignmentResult

    def total_shifts(self) -> int:
        return len(self.snapshot.shifts)

    def total_staff(self) -> int:
        return len(self.snapshot.staff)


def run_staffing_sync(
    *,
    seven_shifts: SevenShiftsClient,
    deputy: DeputyClient,
    bookings: Sequence[BookingWindow],
    start: datetime,
    end: datetime,
) -> StaffingSyncResult:
    """Synchronize staffing data from integrated providers and align with bookings."""

    normalized_start = _ensure_utc(start)
    normalized_end = _ensure_utc(end)

    staff: Dict[str, StaffMember] = {}
    shifts: List[StaffShift] = []

    for record in seven_shifts.fetch_schedules(start=normalized_start, end=normalized_end):
        member, shift = _map_seven_shifts_record(record)
        staff[member.id] = member
        shifts.append(shift)

    for record in deputy.fetch_shifts(start=normalized_start, end=normalized_end):
        member, shift = _map_deputy_record(record)
        staff[member.id] = member
        shifts.append(shift)

    snapshot = StaffingSnapshot(staff=staff, shifts=shifts)
    alignment = reconcile_staff_availability(snapshot.shifts, bookings)
    return StaffingSyncResult(snapshot=snapshot, alignment=alignment)


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------

def _map_seven_shifts_record(record: Dict[str, object]) -> Tuple[StaffMember, StaffShift]:
    user = _as_dict(record.get("user"))
    user_id = _coerce_str(user.get("id") or record.get("user_id") or record.get("employee_id"))
    name = _coerce_str(user.get("name") or record.get("user_name") or "Unknown")
    roles = _normalize_roles(user.get("roles") or record.get("roles") or record.get("role"))

    member = StaffMember(
        id=_staff_key("seven_shifts", user_id),
        external_id=user_id,
        source="seven_shifts",
        name=name,
        email=_coerce_optional(user.get("email")),
        phone=_coerce_optional(user.get("phone")),
        roles=roles,
    )

    shift_id = _coerce_str(record.get("id") or record.get("shift_id") or user_id)
    start = _parse_datetime(record.get("start"))
    end = _parse_datetime(record.get("end"))
    location = _coerce_optional(record.get("location_id") or record.get("location"))
    shift_roles = _normalize_roles(record.get("roles") or record.get("role") or roles)

    metadata = {}
    for key in ("department", "notes", "location_name"):
        if key in record:
            metadata[key] = record[key]

    shift = StaffShift(
        id=_shift_key("seven_shifts", shift_id),
        external_id=shift_id,
        staff_id=member.id,
        source="seven_shifts",
        start=start,
        end=end,
        location_id=location,
        roles=shift_roles,
        metadata=metadata,
    )
    return member, shift


def _map_deputy_record(record: Dict[str, object]) -> Tuple[StaffMember, StaffShift]:
    employee = _as_dict(record.get("employee") or record.get("Employee"))
    employee_id = _coerce_str(
        employee.get("id")
        or employee.get("Id")
        or record.get("employee_id")
        or record.get("EmployeeId")
    )
    name = _coerce_str(
        employee.get("name")
        or employee.get("Name")
        or employee.get("DisplayName")
        or record.get("employee_name")
        or "Unknown"
    )
    roles = _normalize_roles(
        record.get("roles")
        or record.get("role")
        or employee.get("roles")
        or employee.get("Role")
        or record.get("position")
        or record.get("task")
    )

    member = StaffMember(
        id=_staff_key("deputy", employee_id),
        external_id=employee_id,
        source="deputy",
        name=name,
        email=_coerce_optional(employee.get("email") or record.get("employee_email")),
        phone=_coerce_optional(employee.get("phone") or record.get("employee_phone")),
        roles=roles,
    )

    shift_id = _coerce_str(record.get("id") or record.get("Id") or record.get("roster_id") or employee_id)
    start = _parse_datetime(record.get("start") or record.get("StartTime"))
    end = _parse_datetime(record.get("end") or record.get("EndTime"))
    location_source = _as_dict(record.get("location") or record.get("OperationalUnit"))
    location = _coerce_optional(
        record.get("location_id")
        or record.get("LocationId")
        or location_source.get("id")
        or location_source.get("Id")
    )
    shift_roles = _normalize_roles(record.get("roles") or record.get("role") or roles)

    metadata = {}
    for key in ("workarea", "OperationalUnitName", "comments"):
        if key in record:
            metadata[key] = record[key]

    shift = StaffShift(
        id=_shift_key("deputy", shift_id),
        external_id=shift_id,
        staff_id=member.id,
        source="deputy",
        start=start,
        end=end,
        location_id=location,
        roles=shift_roles,
        metadata=metadata,
    )
    return member, shift


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _staff_key(source: str, external_id: str) -> str:
    return f"{source}:{external_id}"


def _shift_key(source: str, external_id: str) -> str:
    return f"{source}:{external_id}"


def _coerce_str(value: object | None) -> str:
    if value is None:
        raise ValueError("Expected non-null identifier")
    return str(value)


def _coerce_optional(value: object | None) -> str | None:
    if value in (None, "", "null"):
        return None
    return str(value)


def _normalize_roles(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, (list, tuple, set)):
        return tuple(str(part).strip() for part in value if str(part).strip())
    return ()


def _parse_datetime(value: object | None) -> datetime:
    if value is None:
        raise ValueError("Missing datetime value in shift record")
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _as_dict(value: object | None) -> Dict[str, object]:
    if isinstance(value, dict):
        return value
    return {}


__all__ = ["run_staffing_sync", "StaffingSyncResult"]
