"""Booking API endpoints with compliance validation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
"""Booking API endpoints with compliance validation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from dateutil.rrule import rrulestr
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from prep.compliance.constants import BOOKING_COMPLIANCE_BANNER
from prep.database.connection import get_db
from prep.insurance.certificates import issue_certificate_for_booking_sync
from prep.models import Booking, BookingStatus, Kitchen, RecurringBookingTemplate
from prep.observability.metrics import DELIVERIES_COUNTER
from prep.settings import get_settings

from .kitchens import analyze_kitchen_compliance

router = APIRouter(prefix="/bookings", tags=["bookings"])


BOOKING_BUFFER = timedelta(minutes=30)


class BookingCreate(BaseModel):
    """Payload used to create a booking."""

    user_id: str
    kitchen_id: str
    start_time: datetime
    end_time: datetime


class BookingResponse(BaseModel):
    """Booking response returned to API consumers."""

    id: str
    user_id: str
    kitchen_id: str
    start_time: datetime
    end_time: datetime
    status: str
    created_at: datetime
    updated_at: datetime

def _advisory_lock_key(kitchen_id: UUID) -> int:
    """Derive a signed 64-bit advisory lock key from a UUID."""

    raw = int.from_bytes(kitchen_id.bytes[:8], byteorder="big", signed=False)
    if raw >= 2**63:
        raw -= 2**64
    return raw


async def _acquire_kitchen_lock(db: AsyncSession, kitchen_id: UUID) -> None:
    """Acquire a transaction-scoped advisory lock for a kitchen."""

    bind = getattr(db, "bind", None)
    if bind is None or getattr(bind.dialect, "name", "") != "postgresql":
        return

    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _advisory_lock_key(kitchen_id)})


async def _find_conflicting_booking(
    db: AsyncSession,
    kitchen_id: UUID,
    start_time: datetime,
    end_time: datetime,
    buffer: timedelta = BOOKING_BUFFER,
) -> Optional[Booking]:
    """Return an existing booking that overlaps the requested window (with buffer)."""

    window_start = start_time - buffer
    window_end = end_time + buffer

    stmt = (
        select(Booking)
        .where(
            Booking.kitchen_id == kitchen_id,
            Booking.status != BookingStatus.CANCELLED,
            Booking.start_time < window_end,
            Booking.end_time > window_start,
        )
        .order_by(Booking.start_time)
        .limit(1)
    )

    result = await db.execute(stmt)
    return result.scalars().first()


class RecurringBookingCreate(BaseModel):
    """Payload describing a recurring booking schedule."""

    user_id: str
    kitchen_id: str
    start_time: datetime
    end_time: datetime
    rrule: str = Field(..., description="iCalendar RRULE describing the recurrence pattern")
    buffer_minutes: int = Field(0, ge=0, le=24 * 60)


class RecurringBookingResponse(BaseModel):
    """Response describing the created recurring template and booking instances."""

    template_id: str
    created_bookings: list[BookingResponse]
    skipped_occurrences: int


def _ensure_timezone(dt: datetime) -> datetime:
    """Return a timezone-aware datetime in UTC."""

    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_data: BookingCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> BookingResponse:
    """Create a booking after verifying kitchen compliance."""

    settings = get_settings()

    if settings.compliance_controls_enabled:
        def _normalize(dt: datetime) -> datetime:
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt

        start_dt = _normalize(booking_data.start_time)
        end_dt = _normalize(booking_data.end_time)

        if start_dt.weekday() >= 5 or end_dt.weekday() >= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BOOKING_COMPLIANCE_BANNER,
            )

        start_minutes = start_dt.hour * 60 + start_dt.minute
        end_minutes = end_dt.hour * 60 + end_dt.minute
        earliest_minutes = 8 * 60
        latest_minutes = 13 * 60

        if start_minutes < earliest_minutes or end_minutes > latest_minutes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BOOKING_COMPLIANCE_BANNER,
            )

    try:
        kitchen_uuid = uuid.UUID(booking_data.kitchen_id)
        user_uuid = uuid.UUID(booking_data.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid identifier") from exc

    kitchen = await db.get(Kitchen, kitchen_uuid)
    if kitchen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")

    compliance_status = kitchen.compliance_status or "unknown"
    if compliance_status == "non_compliant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This kitchen is not compliant with current regulations and cannot be booked.",
        )

    if kitchen.last_compliance_check:
        if (datetime.utcnow() - kitchen.last_compliance_check) > timedelta(days=30):
            background_tasks.add_task(analyze_kitchen_compliance, str(kitchen.id))

    await _acquire_kitchen_lock(db, kitchen_uuid)

    conflict = await _find_conflicting_booking(
        db,
        kitchen_uuid,
        booking_data.start_time,
        booking_data.end_time,
    )

    if conflict:
        await db.rollback()
        buffer_minutes = int(BOOKING_BUFFER.total_seconds() // 60)
        message = (
            "Requested booking overlaps with an existing booking from "
            f"{conflict.start_time.isoformat()} to {conflict.end_time.isoformat()} "
            f"including a {buffer_minutes}-minute buffer."
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)

    new_booking = Booking(
        customer_id=user_uuid,
        host_id=kitchen.host_id,
        kitchen_id=kitchen_uuid,
        start_time=booking_data.start_time,
        end_time=booking_data.end_time,
        status=BookingStatus.PENDING,
    )

    db.add(new_booking)
    await db.commit()
    await db.refresh(new_booking)

    background_tasks.add_task(issue_certificate_for_booking_sync, str(new_booking.id))
    DELIVERIES_COUNTER.inc()

    return BookingResponse(
        id=str(new_booking.id),
        user_id=str(new_booking.customer_id),
        kitchen_id=str(new_booking.kitchen_id),
        start_time=new_booking.start_time,
        end_time=new_booking.end_time,
        status=new_booking.status.value,
        created_at=new_booking.created_at,
        updated_at=new_booking.updated_at,
    )


@router.post(
    "/recurring",
    response_model=RecurringBookingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recurring_booking(
    booking_data: RecurringBookingCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RecurringBookingResponse:
    """Create a recurring booking template and instantiate bookings for the next 60 days."""

    try:
        kitchen_uuid = uuid.UUID(booking_data.kitchen_id)
        user_uuid = uuid.UUID(booking_data.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid identifier") from exc

    normalized_start = _ensure_timezone(booking_data.start_time)
    normalized_end = _ensure_timezone(booking_data.end_time)
    if normalized_end <= normalized_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be after start_time",
        )

    try:
        rule = rrulestr(booking_data.rrule, dtstart=normalized_start)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid recurrence rule") from exc

    kitchen = await db.get(Kitchen, kitchen_uuid)
    if kitchen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")

    compliance_status = kitchen.compliance_status or "unknown"
    if compliance_status == "non_compliant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This kitchen is not compliant with current regulations and cannot be booked.",
        )

    if kitchen.last_compliance_check:
        if (datetime.utcnow() - kitchen.last_compliance_check) > timedelta(days=30):
            background_tasks.add_task(analyze_kitchen_compliance, str(kitchen.id))

    window_start = datetime.now(UTC)
    window_end = window_start + timedelta(days=60)
    duration = normalized_end - normalized_start
    buffer_delta = timedelta(minutes=booking_data.buffer_minutes)

    template = RecurringBookingTemplate(
        kitchen_id=kitchen_uuid,
        host_id=kitchen.host_id,
        customer_id=user_uuid,
        start_time=normalized_start,
        end_time=normalized_end,
        rrule=booking_data.rrule,
        buffer_minutes=booking_data.buffer_minutes,
    )
    db.add(template)

    existing_bookings_query = (
        select(Booking)
        .where(Booking.kitchen_id == kitchen_uuid)
        .where(Booking.status != BookingStatus.CANCELLED)
        .where(Booking.start_time < window_end + buffer_delta)
        .where(Booking.end_time > window_start - buffer_delta)
    )
    existing_bookings = list((await db.execute(existing_bookings_query)).scalars().all())
    blocked_windows: list[tuple[datetime, datetime]] = [
        (
            _ensure_timezone(existing.start_time) - buffer_delta,
            _ensure_timezone(existing.end_time) + buffer_delta,
        )
        for existing in existing_bookings
    ]

    created_bookings: list[Booking] = []
    skipped_occurrences = 0
    for occurrence_start in rule.between(window_start, window_end, inc=True):
        occurrence_start = _ensure_timezone(occurrence_start)
        occurrence_end = occurrence_start + duration
        if occurrence_end <= window_start:
            continue

        buffered_start = occurrence_start - buffer_delta
        buffered_end = occurrence_end + buffer_delta
        conflict = any(
            not (buffered_end <= blocked_start or buffered_start >= blocked_end)
            for blocked_start, blocked_end in blocked_windows
        )
        if conflict:
            skipped_occurrences += 1
            continue

        booking = Booking(
            customer_id=user_uuid,
            host_id=kitchen.host_id,
            kitchen_id=kitchen_uuid,
            start_time=occurrence_start,
            end_time=occurrence_end,
            status=BookingStatus.PENDING,
        )
        db.add(booking)
        created_bookings.append(booking)
        blocked_windows.append((buffered_start, buffered_end))

    await db.commit()

    await db.refresh(template)
    for booking in created_bookings:
        await db.refresh(booking)
        background_tasks.add_task(issue_certificate_for_booking_sync, str(booking.id))
        DELIVERIES_COUNTER.inc()

    return RecurringBookingResponse(
        template_id=str(template.id),
        created_bookings=[
            BookingResponse(
                id=str(booking.id),
                user_id=str(booking.customer_id),
                kitchen_id=str(booking.kitchen_id),
                start_time=booking.start_time,
                end_time=booking.end_time,
                status=booking.status.value,
                created_at=booking.created_at,
                updated_at=booking.updated_at,
            )
            for booking in created_bookings
        ],
        skipped_occurrences=skipped_occurrences,
    )
