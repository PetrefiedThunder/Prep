from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from codex import config, database
from codex.models import Base, Booking, BookingStatus, Kitchen, User, UserRole


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    database.reset_engine_cache()
    config.reset_settings_cache()
    monkeypatch.delenv("CODEX_DATABASE_URL", raising=False)
    monkeypatch.delenv("CODEX_ENVIRONMENT", raising=False)
    yield
    database.reset_engine_cache()
    config.reset_settings_cache()


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_settings_defaults():
    settings = config.load_settings(env={})
    assert settings.environment == "development"
    assert settings.database_url == "sqlite+aiosqlite:///./codex.db"


def test_settings_environment_override(monkeypatch):
    monkeypatch.setenv("CODEX_ENVIRONMENT", "staging")
    monkeypatch.setenv("CODEX_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    config.reset_settings_cache()

    settings = config.get_settings()

    assert settings.environment == "staging"
    assert settings.database_url == "sqlite+aiosqlite:///:memory:"


@pytest.mark.anyio
async def test_engine_roundtrip(monkeypatch):
    monkeypatch.setenv("CODEX_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    config.reset_settings_cache()
    database.reset_engine_cache()

    engine = database.get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = database.get_session_factory()
    async with session_factory() as session:
        await _seed_sample_data(session)

    async with session_factory() as session:
        assert isinstance(session, AsyncSession)
        result = await session.execute(select(Kitchen).options(selectinload(Kitchen.owner)))
        kitchen = result.scalar_one()
        assert kitchen.owner.email == "host@example.com"

        booking = (await session.execute(select(Booking))).scalar_one()
        assert booking.status is BookingStatus.PENDING
        assert booking.duration() == timedelta(hours=2)


async def _seed_sample_data(session: AsyncSession) -> None:
    host = User(
        email="host@example.com",
        full_name="Host User",
        hashed_password="hashed",
        role=UserRole.HOST,
    )
    customer = User(
        email="customer@example.com",
        full_name="Customer",
        hashed_password="hashed",
        role=UserRole.CUSTOMER,
    )
    kitchen = Kitchen(
        owner=host,
        name="Downtown Kitchen",
        city="Austin",
        state="TX",
        hourly_rate=Decimal("45.00"),
        capacity=15,
    )
    start_time = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)
    booking = Booking(
        kitchen=kitchen,
        host=host,
        customer=customer,
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        total_amount=Decimal("90.00"),
    )
    session.add_all([host, customer, kitchen, booking])
    await session.commit()
