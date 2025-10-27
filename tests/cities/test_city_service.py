from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from fnmatch import fnmatch
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.cache import RedisProtocol
from prep.cities.schemas import BookingQuoteRequest, CityLaunchRequest
from prep.cities.service import CityExpansionService
from prep.matching.service import MatchingService
from prep.models.orm import (
    Base,
    Booking,
    BookingStatus,
    Kitchen,
    KitchenMatchingProfile,
    User,
)


class _StubRedis(RedisProtocol):
    """Minimal in-memory Redis replacement for tests."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    async def get(self, key: str) -> Any:
        return self._store.get(key)

    async def setex(self, key: str, ttl: int, value: Any) -> None:
        self._store[key] = value

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self._store:
                self._store.pop(key, None)
                removed += 1
        return removed

    async def keys(self, pattern: str) -> list[str]:
        return [key for key in self._store if fnmatch(key, pattern)]


@pytest.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture()
def anyio_backend() -> str:
    """Restrict AnyIO tests to asyncio backend for local sqlite compatibility."""

    return "asyncio"


async def _seed_city(session: AsyncSession) -> dict[str, UUID]:
    host = User(email="host@example.com", full_name="Jordan Host")
    customer = User(email="customer@example.com", full_name="Riley Customer")
    session.add_all([host, customer])
    await session.flush()

    kitchen = Kitchen(
        name="Mission Culinary Lab",
        host_id=host.id,
        city="San Francisco",
        state="CA",
        hourly_rate=85,
        trust_score=4.6,
        moderation_status="approved",
        certification_status="approved",
        published=True,
    )
    session.add(kitchen)
    await session.flush()

    profile = KitchenMatchingProfile(
        kitchen_id=kitchen.id,
        equipment=["oven", "walk-in fridge"],
        cuisines=["californian"],
        availability=["weekend", "evening"],
    )
    session.add(profile)

    recent_start = datetime.now(UTC) - timedelta(days=7)
    booking = Booking(
        host_id=host.id,
        customer_id=customer.id,
        kitchen_id=kitchen.id,
        status=BookingStatus.COMPLETED,
        start_time=recent_start,
        end_time=recent_start + timedelta(hours=5),
        total_amount=420.0,
        platform_fee=42.0,
        host_payout_amount=378.0,
        payment_method="card",
    )
    session.add(booking)

    earlier_start = datetime.now(UTC) - timedelta(days=70)
    historical_booking = Booking(
        host_id=host.id,
        customer_id=customer.id,
        kitchen_id=kitchen.id,
        status=BookingStatus.COMPLETED,
        start_time=earlier_start,
        end_time=earlier_start + timedelta(hours=4),
        total_amount=360.0,
        platform_fee=36.0,
        host_payout_amount=324.0,
        payment_method="card",
    )
    session.add(historical_booking)

    await session.commit()
    return {"kitchen_id": kitchen.id}


@pytest.mark.anyio("asyncio")
async def test_city_market_analytics_exposes_confidence(session: AsyncSession) -> None:
    await _seed_city(session)
    redis = _StubRedis()
    matching = MatchingService(session, redis)
    service = CityExpansionService(session, redis, matching_service=matching)

    analytics = await service.get_city_analytics("San Francisco")

    assert analytics.city == "San Francisco"
    assert analytics.metrics.kitchen_count == 1
    assert analytics.top_kitchens, "Expected top kitchens to be populated"
    assert any(signal.metric == "kitchen_sample" for signal in analytics.confidence)


@pytest.mark.anyio("asyncio")
async def test_currency_rates_and_quote_generation(session: AsyncSession) -> None:
    ids = await _seed_city(session)
    redis = _StubRedis()
    matching = MatchingService(session, redis)
    service = CityExpansionService(session, redis, matching_service=matching)

    base, rates, timestamp = await service.get_currency_rates("USD")
    assert base == "USD"
    assert "EUR" in rates
    assert timestamp.tzinfo is not None

    quote = await service.quote_booking(
        BookingQuoteRequest(kitchen_id=ids["kitchen_id"], hours=4, currency="EUR")
    )
    assert quote.converted_total_cost is not None
    assert quote.target_currency == "EUR"


@pytest.mark.anyio("asyncio")
async def test_launch_lifecycle_creates_plan_and_readiness(session: AsyncSession) -> None:
    await _seed_city(session)
    redis = _StubRedis()
    matching = MatchingService(session, redis)
    service = CityExpansionService(session, redis, matching_service=matching)

    launch = await service.initialize_launch("San Francisco", CityLaunchRequest(lead_owner="Ops"))
    assert launch.plan, "Expected launch plan to include steps"

    readiness = await service.get_launch_readiness("San Francisco")
    assert readiness.city == "San Francisco"
    assert readiness.checklist, "Expected readiness checklist entries"
