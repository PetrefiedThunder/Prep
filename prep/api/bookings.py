"""Booking API endpoints with compliance validation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from prep.compliance.constants import BOOKING_COMPLIANCE_BANNER
from prep.database.connection import get_db
from prep.models import Booking, BookingStatus, Kitchen
from prep.settings import get_settings

from .kitchens import analyze_kitchen_compliance

router = APIRouter(prefix="/bookings", tags=["bookings"])


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
