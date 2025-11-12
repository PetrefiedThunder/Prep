from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.api.bookings import BOOKING_BUFFER, _acquire_kitchen_lock, _find_conflicting_booking
from prep.models.orm import Base, Booking, BookingStatus, Kitchen, User


@pytest.mark.anyio
async def test_conflict_detection_includes_buffer() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )

    try:
        async with session_factory() as session:
            host = User(email="host@example.com", full_name="Host User", is_active=True)
            customer = User(email="guest@example.com", full_name="Guest User", is_active=True)
            session.add_all([host, customer])
            await session.flush()

            kitchen = Kitchen(name="Prep Kitchen", host_id=host.id)
            session.add(kitchen)
            await session.flush()

            base_start = datetime(2024, 1, 5, 10, 0, tzinfo=UTC)
            base_end = base_start + timedelta(hours=4)

            booking = Booking(
                host_id=host.id,
                customer_id=customer.id,
                kitchen_id=kitchen.id,
                status=BookingStatus.CONFIRMED,
                start_time=base_start,
                end_time=base_end,
            )
            session.add(booking)
            await session.commit()

            conflicting_start = base_end + BOOKING_BUFFER - timedelta(minutes=10)
            conflicting_end = conflicting_start + timedelta(hours=2)

            conflict = await _find_conflicting_booking(
                session,
                kitchen.id,
                conflicting_start,
                conflicting_end,
            )
            assert conflict is not None

            available_start = base_end + BOOKING_BUFFER + timedelta(minutes=5)
            available_end = available_start + timedelta(hours=2)

            available = await _find_conflicting_booking(
                session,
                kitchen.id,
                available_start,
                available_end,
            )
            assert available is None
    finally:
        await engine.dispose()


class _FakeSession:
    """Minimal async session stub that simulates advisory locks."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.lock_keys: list[int] = []
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Any:
        if "pg_advisory_xact_lock" in getattr(statement, "text", str(statement)):
            await self._lock.acquire()
            self.lock_keys.append(params["key"] if params else None)
            return SimpleNamespace()
        raise AssertionError("Unexpected statement executed")

    async def release_lock(self) -> None:
        if self._lock.locked():
            self._lock.release()
        await asyncio.sleep(0)


@pytest.mark.anyio
async def test_acquire_kitchen_lock_serializes_concurrent_calls() -> None:
    session = _FakeSession()
    kitchen_id = uuid4()
    order: list[str] = []
    release_first = asyncio.Event()
    second_ready = asyncio.Event()

    async def first() -> None:
        await _acquire_kitchen_lock(session, kitchen_id)
        order.append("first")
        second_ready.set()
        await release_first.wait()
        await session.release_lock()

    async def second() -> None:
        await second_ready.wait()
        await _acquire_kitchen_lock(session, kitchen_id)
        order.append("second")
        await session.release_lock()

    first_task = asyncio.create_task(first())
    second_task = asyncio.create_task(second())

    await asyncio.sleep(0.05)
    assert order == ["first"]

    release_first.set()
    await asyncio.gather(first_task, second_task)

    assert order == ["first", "second"]
    assert len(session.lock_keys) == 2
    assert session.lock_keys[0] == session.lock_keys[1]
