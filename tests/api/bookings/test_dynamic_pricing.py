"""Tests for dynamic pricing integration in the bookings API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import AsyncGenerator, Iterator
from uuid import uuid4

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.pricing.dynamic_rules import (
    DynamicPricingRuleEngine,
    UnderUtilizationRule,
    UtilizationMetrics,
)
from prep.api.bookings import router as bookings_router
from prep.database.connection import get_db
from prep.models.orm import Base, Kitchen, User
from prep.settings import get_settings

pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()


@pytest.fixture()
async def app() -> AsyncGenerator[FastAPI, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    application = FastAPI()
    application.include_router(bookings_router)
    application.dependency_overrides[get_db] = _override_get_db
    application.state.session_factory = session_factory

    try:
        yield application
    finally:
        await engine.dispose()


@pytest.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


async def _seed_user_and_kitchen(
    app: FastAPI,
    *,
    utilization_rate: float,
    hourly_rate: Decimal = Decimal("120.00"),
) -> tuple[str, str]:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        host = User(
            email="host@example.com",
            full_name="Host User",
            hashed_password="hashed",
        )
        session.add(host)
        await session.flush()

        customer = User(
            email="customer@example.com",
            full_name="Customer User",
            hashed_password="hashed",
        )
        session.add(customer)
        await session.flush()

        kitchen = Kitchen(
            id=uuid4(),
            host_id=host.id,
            name="Dynamic Kitchen",
            compliance_status="compliant",
            city="Austin",
            state="TX",
            hourly_rate=hourly_rate,
            pricing={"utilization_rate": utilization_rate},
        )
        session.add(kitchen)
        await session.commit()

        return str(customer.id), str(kitchen.id)


async def _post_booking(
    client: AsyncClient,
    *,
    user_id: str,
    kitchen_id: str,
    start: datetime,
    end: datetime,
) -> Response:
    payload = {
        "user_id": user_id,
        "kitchen_id": kitchen_id,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
    }
    return await client.post("/bookings/", json=payload)


async def test_low_utilization_triggers_discount(app: FastAPI, client: AsyncClient) -> None:
    user_id, kitchen_id = await _seed_user_and_kitchen(app, utilization_rate=0.3)

    now = datetime.now(timezone.utc)
    start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=2)

    response = await _post_booking(
        client,
        user_id=user_id,
        kitchen_id=kitchen_id,
        start=start,
        end=end,
    )
    body = response.json()

    assert response.status_code == 201
    assert body["discount_percent"] == pytest.approx(0.15)
    assert body["total_amount"] == pytest.approx(204.0)
    assert "low_utilization" in body["pricing_adjustments"]


async def test_high_utilization_applies_no_discount(app: FastAPI, client: AsyncClient) -> None:
    user_id, kitchen_id = await _seed_user_and_kitchen(app, utilization_rate=0.85)

    now = datetime.now(timezone.utc)
    start = now.replace(hour=10, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=3)

    response = await _post_booking(
        client,
        user_id=user_id,
        kitchen_id=kitchen_id,
        start=start,
        end=end,
    )
    body = response.json()

    assert response.status_code == 201
    assert body["discount_percent"] is None
    assert body["total_amount"] == pytest.approx(360.0)
    assert body["pricing_adjustments"] == []


def test_rule_engine_under_utilization() -> None:
    engine = DynamicPricingRuleEngine([UnderUtilizationRule(threshold=0.5, discount=0.2)])
    metrics = UtilizationMetrics(utilization_rate=0.3)

    decision = engine.evaluate(metrics)

    assert decision.discount == pytest.approx(0.2)
    assert decision.applied_rules == ["low_utilization"]
