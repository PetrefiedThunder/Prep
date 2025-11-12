from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.api.bookings import (
    RecurringBookingCreate,
    create_recurring_booking,
)
from prep.models.orm import Base, Booking, BookingStatus, Kitchen, RecurringBookingTemplate, User


@pytest.fixture()
async def session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


async def _create_user(session: AsyncSession, *, email: str) -> User:
    user = User(
        id=uuid4(),
        email=email,
        full_name=email.split("@", 1)[0],
        hashed_password="hashed",
    )
    session.add(user)
    await session.flush()
    return user


async def _create_kitchen(session: AsyncSession, host: User) -> Kitchen:
    kitchen = Kitchen(
        id=uuid4(),
        host_id=host.id,
        name="Recurring Kitchen",
        city="Austin",
        state="TX",
        hourly_rate=120,
        published=True,
    )
    session.add(kitchen)
    await session.flush()
    return kitchen


@pytest.mark.anyio
async def test_invalid_rrule_raises_http_400(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        host = await _create_user(session, email="host@example.com")
        customer = await _create_user(session, email="guest@example.com")
        kitchen = await _create_kitchen(session, host)
        await session.commit()

        payload = RecurringBookingCreate(
            user_id=str(customer.id),
            kitchen_id=str(kitchen.id),
            start_time=datetime.now(UTC) + timedelta(days=1),
            end_time=datetime.now(UTC) + timedelta(days=1, hours=2),
            rrule="INVALID",
            buffer_minutes=15,
        )

        with pytest.raises(HTTPException) as excinfo:
            await create_recurring_booking(payload, BackgroundTasks(), session)

        assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
        assert excinfo.value.detail == "Invalid recurrence rule"


@pytest.mark.anyio
async def test_recurring_schedule_honors_buffer(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        host = await _create_user(session, email="host@example.com")
        customer = await _create_user(session, email="guest@example.com")
        kitchen = await _create_kitchen(session, host)

        start = (datetime.now(UTC) + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=2)

        conflicting = Booking(
            id=uuid4(),
            customer_id=customer.id,
            host_id=host.id,
            kitchen_id=kitchen.id,
            status=BookingStatus.CONFIRMED,
            start_time=end + timedelta(minutes=30),
            end_time=end + timedelta(hours=2),
        )
        session.add(conflicting)
        await session.commit()

        payload = RecurringBookingCreate(
            user_id=str(customer.id),
            kitchen_id=str(kitchen.id),
            start_time=start,
            end_time=end,
            rrule="FREQ=DAILY;COUNT=3",
            buffer_minutes=60,
        )

        response = await create_recurring_booking(payload, BackgroundTasks(), session)

        bookings = (
            (
                await session.execute(
                    select(Booking)
                    .where(Booking.kitchen_id == kitchen.id)
                    .order_by(Booking.start_time)
                )
            )
            .scalars()
            .all()
        )

        assert response.skipped_occurrences >= 1
        assert (
            len(response.created_bookings) == len(bookings) - 1
        )  # exclude the seeded conflicting booking

        template = (
            await session.execute(
                select(RecurringBookingTemplate).where(
                    RecurringBookingTemplate.kitchen_id == kitchen.id
                )
            )
        ).scalar_one()
        assert template.buffer_minutes == 60
