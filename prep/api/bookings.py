"""Booking API endpoints with compliance validation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database.connection import get_db
from prep.models import Booking, BookingStatus, Kitchen

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


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_data: BookingCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> BookingResponse:
    """Create a booking after verifying kitchen compliance."""

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
