"""Booking API endpoints with compliance validation and dynamic pricing."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from dateutil.rrule import rrulestr
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.pricing import UtilizationMetrics, build_default_engine
from prep.auth import User, get_current_user_optional
from prep.compliance.constants import BOOKING_COMPLIANCE_BANNER, BOOKING_PILOT_BANNER
from prep.database.connection import get_db
from prep.models import Booking, BookingStatus, Kitchen, RecurringBookingTemplate
from prep.pilot.utils import is_pilot_location
from prep.settings import get_settings

<<<<<<< HEAD
=======
logger = logging.getLogger(__name__)

>>>>>>> origin/main
try:
    from prep.insurance.certificates import (
        issue_certificate_for_booking_sync as _issue_certificate_for_booking_sync,
    )
except ModuleNotFoundError:  # Optional dependency for isolated test runs
    _issue_certificate_for_booking_sync = None
<<<<<<< HEAD
    logging.getLogger(__name__).debug(
        "prep.insurance.certificates not available; certificate tasks disabled"
    )
=======
    logger.debug("prep.insurance.certificates not available; certificate tasks disabled")
>>>>>>> origin/main

try:
    from prep.observability.metrics import DELIVERIES_COUNTER as _DELIVERIES_COUNTER
except ModuleNotFoundError:  # Optional dependency for isolated test runs
    class _NullCounter:
        def inc(self, amount: int | float = 1) -> None:
            return None

    _DELIVERIES_COUNTER = _NullCounter()
<<<<<<< HEAD
    logging.getLogger(__name__).debug("prometheus metrics not available; delivery counter disabled")

logger = logging.getLogger(__name__)
=======
    logger.debug("prometheus metrics not available; delivery counter disabled")
>>>>>>> origin/main

router = APIRouter(prefix="/bookings", tags=["bookings"])


BOOKING_BUFFER = timedelta(minutes=30)


_ZIP_PATTERN = re.compile(r"\b\d{5}(?:-\d{4})?\b")


def _schedule_certificate(background_tasks: BackgroundTasks, booking_id: uuid.UUID) -> None:
    """Schedule certificate issuance if the dependency is available."""

    if _issue_certificate_for_booking_sync is None:
        logger.debug("Skipping certificate issuance for %s; dependency unavailable", booking_id)
        return
    background_tasks.add_task(_issue_certificate_for_booking_sync, str(booking_id))


def _increment_deliveries() -> None:
    """Increment deliveries counter if metrics are configured."""

    try:
        _DELIVERIES_COUNTER.inc()
    except Exception:
        logger.debug("Skipping deliveries counter increment; metrics unavailable", exc_info=True)


def _schedule_compliance_analysis(background_tasks: BackgroundTasks, kitchen_id: uuid.UUID) -> None:
    """Schedule compliance analysis without importing the kitchens module eagerly."""

    try:
        from .kitchens import analyze_kitchen_compliance
    except ModuleNotFoundError:
        logger.debug("prep.api.kitchens not available; skipping compliance analysis task")
        return

    background_tasks.add_task(analyze_kitchen_compliance, str(kitchen_id))


def _determine_pilot_mode(kitchen: Kitchen) -> tuple[bool, str]:
    """Return whether the kitchen is in pilot mode and the applicable banner."""

    zip_code = None
    if kitchen.address:
        match = _ZIP_PATTERN.search(kitchen.address)
        if match:
            zip_code = match.group(0)

    county = None
    if isinstance(kitchen.insurance_info, dict):
        county = kitchen.insurance_info.get("county") or kitchen.insurance_info.get("county_name")

    pilot_mode = is_pilot_location(
        state=kitchen.state,
        city=kitchen.city,
        county=county,
        zip_code=zip_code,
    )
    banner = BOOKING_PILOT_BANNER if pilot_mode else BOOKING_COMPLIANCE_BANNER
    return pilot_mode, banner


def _build_utilization_metrics(kitchen: Kitchen) -> UtilizationMetrics:
    """Construct utilization metrics from a kitchen's pricing metadata."""

    pricing_payload = kitchen.pricing or {}
    try:
        utilization = float(pricing_payload.get("utilization_rate", 1.0))
    except (TypeError, ValueError):
        utilization = 1.0
    try:
        active = int(pricing_payload.get("active_bookings", 0))
    except (TypeError, ValueError):
        active = 0
    try:
        cancellation_rate = float(pricing_payload.get("cancellation_rate", 0.0))
    except (TypeError, ValueError):
        cancellation_rate = 0.0

    return UtilizationMetrics(
        utilization_rate=utilization,
        active_bookings=active,
        cancellation_rate=cancellation_rate,
    )


def _calculate_dynamic_price(
    kitchen: Kitchen, start_time: datetime, end_time: datetime
) -> tuple[Decimal, float, list[str]]:
    """Return the total amount, discount percent, and applied rules."""

    engine = build_default_engine()
    metrics = _build_utilization_metrics(kitchen)
    decision = engine.evaluate(metrics)

    if kitchen.hourly_rate is None:
        return Decimal("0.00"), decision.discount, decision.applied_rules

    base_rate = Decimal(kitchen.hourly_rate)
    duration_seconds = Decimal(str((end_time - start_time).total_seconds()))
    hours = duration_seconds / Decimal("3600")
    subtotal = (base_rate * hours).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    discount_multiplier = Decimal("1") - Decimal(str(decision.discount))
    discount_multiplier = max(discount_multiplier, Decimal("0"))
    total = (subtotal * discount_multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return total, decision.discount, decision.applied_rules


class BookingCreate(BaseModel):
    """Payload used to create a booking."""

    kitchen_id: str
    start_time: datetime
    end_time: datetime
    user_id: str | None = None


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
    total_amount: float | None = None
    discount_percent: float | None = None
    pricing_adjustments: list[str] = Field(default_factory=list)


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

    await db.execute(
        text("SELECT pg_advisory_xact_lock(:key)"), {"key": _advisory_lock_key(kitchen_id)}
    )


async def _find_conflicting_booking(
    db: AsyncSession,
    kitchen_id: UUID,
    start_time: datetime,
    end_time: datetime,
    buffer: timedelta = BOOKING_BUFFER,
) -> Booking | None:
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

    kitchen_id: str
    start_time: datetime
    end_time: datetime
    rrule: str = Field(..., description="iCalendar RRULE describing the recurrence pattern")
    buffer_minutes: int = Field(0, ge=0, le=24 * 60)
    user_id: str | None = None


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
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> BookingResponse:
    """Create a booking after verifying kitchen compliance."""

    settings = get_settings()

    user_identifier = current_user.id if current_user else booking_data.user_id
    if not user_identifier:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    try:
        kitchen_uuid = uuid.UUID(booking_data.kitchen_id)
        user_uuid = uuid.UUID(user_identifier)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid identifier"
        ) from exc

    kitchen = await db.get(Kitchen, kitchen_uuid)
    if kitchen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")

    pilot_mode, compliance_banner = _determine_pilot_mode(kitchen)

    if settings.compliance_controls_enabled:

        def _normalize(dt: datetime) -> datetime:
            return dt.astimezone(UTC) if dt.tzinfo else dt

        start_dt = _normalize(booking_data.start_time)
        end_dt = _normalize(booking_data.end_time)

        if start_dt.weekday() >= 5 or end_dt.weekday() >= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=compliance_banner,
            )

        start_minutes = start_dt.hour * 60 + start_dt.minute
        end_minutes = end_dt.hour * 60 + end_dt.minute
        earliest_minutes = 8 * 60
        latest_minutes = 13 * 60

        if start_minutes < earliest_minutes or end_minutes > latest_minutes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=compliance_banner,
            )

    compliance_status = kitchen.compliance_status or "unknown"
    if compliance_status == "non_compliant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This kitchen is not compliant with current regulations and cannot be booked.",
        )

    if kitchen.last_compliance_check:
        if (datetime.now(UTC) - kitchen.last_compliance_check) > timedelta(days=30):
            _schedule_compliance_analysis(background_tasks, kitchen.id)

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

    total_amount, discount_percent, adjustments = _calculate_dynamic_price(
        kitchen, booking_data.start_time, booking_data.end_time
    )
    new_booking.total_amount = total_amount

    db.add(new_booking)
    await db.commit()
    await db.refresh(new_booking)

    _schedule_certificate(background_tasks, new_booking.id)
    _increment_deliveries()

    return BookingResponse(
        id=str(new_booking.id),
        user_id=str(new_booking.customer_id),
        kitchen_id=str(new_booking.kitchen_id),
        start_time=new_booking.start_time,
        end_time=new_booking.end_time,
        status=new_booking.status.value,
        created_at=new_booking.created_at,
        updated_at=new_booking.updated_at,
        total_amount=float(total_amount),
        discount_percent=discount_percent if discount_percent else None,
        pricing_adjustments=adjustments,
    )


@router.post(
    "/recurring",
    response_model=RecurringBookingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recurring_booking(
    booking_data: RecurringBookingCreate,
    background_tasks: BackgroundTasks,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> RecurringBookingResponse:
    """Create a recurring booking template and instantiate bookings for the next 60 days."""

    user_identifier = current_user.id if current_user else booking_data.user_id
    if not user_identifier:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    try:
        kitchen_uuid = uuid.UUID(booking_data.kitchen_id)
        user_uuid = uuid.UUID(user_identifier)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid identifier"
        ) from exc

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid recurrence rule"
        ) from exc

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
        if (datetime.now(UTC) - kitchen.last_compliance_check) > timedelta(days=30):
            _schedule_compliance_analysis(background_tasks, kitchen.id)

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
    pricing_snapshots: list[tuple[Booking, float, list[str]]] = []
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
        total_amount, discount_percent, adjustments = _calculate_dynamic_price(
            kitchen, occurrence_start, occurrence_end
        )
        booking.total_amount = total_amount

        db.add(booking)
        created_bookings.append(booking)
        pricing_snapshots.append((booking, discount_percent, adjustments))
        blocked_windows.append((buffered_start, buffered_end))

    await db.commit()

    await db.refresh(template)
    for booking in created_bookings:
        await db.refresh(booking)
        _schedule_certificate(background_tasks, booking.id)
        _increment_deliveries()

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
                total_amount=float(booking.total_amount),
                discount_percent=discount if discount else None,
                pricing_adjustments=adjustments,
            )
            for booking, discount, adjustments in pricing_snapshots
        ],
        skipped_occurrences=skipped_occurrences,
    )
