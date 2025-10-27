"""Tests for the platform payments intent endpoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, AsyncGenerator
from uuid import uuid4

import pytest
import stripe
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import Mock

from prep.cache import RedisProtocol, get_redis
from prep.database import get_db
from prep.models.orm import Base, Booking, Kitchen, User, UserRole
from prep.platform.api import router as platform_router
from prep.settings import Settings, get_settings


class _AsyncSessionFactory:
    """Expose an async session factory via FastAPI state."""

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._factory() as session:
            yield session


class DummyRedis(RedisProtocol):  # type: ignore[misc]
    async def get(self, key: str) -> Any:
        return None

    async def setex(self, key: str, ttl: int, value: Any) -> None:
        return None


@pytest.fixture()
async def app() -> AsyncGenerator[FastAPI, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    state_factory = _AsyncSessionFactory(session_factory)

    application = FastAPI()
    application.include_router(platform_router)
    application.state.sessions = state_factory

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with state_factory.session() as session:
            yield session

    async def _override_get_redis() -> RedisProtocol:
        return DummyRedis()

    settings = Settings()
    settings.stripe_api_key = "sk_test_123"

    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[get_redis] = _override_get_redis

    try:
        yield application
    finally:
        await engine.dispose()


@pytest.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


async def _create_booking(app: FastAPI) -> Booking:
    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        host = User(
            email="host@example.com",
            full_name="Host Example",
            role=UserRole.HOST,
            is_active=True,
        )
        customer = User(
            email="customer@example.com",
            full_name="Customer Example",
            role=UserRole.CUSTOMER,
            is_active=True,
        )
        session.add_all([host, customer])
        await session.flush()

        kitchen = Kitchen(host_id=host.id, name="Test Kitchen")
        session.add(kitchen)
        await session.flush()

        start = datetime.now(UTC)
        booking = Booking(
            kitchen_id=kitchen.id,
            host_id=host.id,
            customer_id=customer.id,
            start_time=start,
            end_time=start + timedelta(hours=2),
            total_amount=Decimal("100.00"),
            platform_fee=Decimal("10.00"),
            host_payout_amount=Decimal("90.00"),
            payment_method="card",
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)
        return booking


@pytest.mark.anyio("asyncio")
async def test_create_payment_intent_success(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    booking = await _create_booking(app)

    payment_intent_create = Mock(
        return_value=SimpleNamespace(id="pi_123", client_secret="cs_test_123")
    )
    monkeypatch.setattr("stripe.PaymentIntent.create", payment_intent_create)

    response = await client.post(
        "/api/v1/platform/payments/intent",
        json={
            "booking_id": str(booking.id),
            "amount": 12345,
            "currency": "USD",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"client_secret": "cs_test_123"}

    payment_intent_create.assert_called_once_with(
        amount=12345,
        currency="usd",
        metadata={"booking_id": str(booking.id)},
        automatic_payment_methods={"enabled": True},
    )

    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        refreshed = await session.get(Booking, booking.id)
        assert refreshed is not None
        assert refreshed.stripe_payment_intent_id == "pi_123"


@pytest.mark.anyio("asyncio")
async def test_create_payment_intent_missing_booking_returns_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    payment_intent_create = Mock()
    monkeypatch.setattr("stripe.PaymentIntent.create", payment_intent_create)

    response = await client.post(
        "/api/v1/platform/payments/intent",
        json={
            "booking_id": str(uuid4()),
            "amount": 5000,
            "currency": "usd",
        },
    )

    assert response.status_code == 404
    payment_intent_create.assert_not_called()


@pytest.mark.anyio("asyncio")
async def test_create_payment_intent_handles_stripe_error(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    booking = await _create_booking(app)

    monkeypatch.setattr(
        "stripe.PaymentIntent.create",
        Mock(side_effect=stripe.error.APIConnectionError("boom")),
    )

    response = await client.post(
        "/api/v1/platform/payments/intent",
        json={
            "booking_id": str(booking.id),
            "amount": 1234,
            "currency": "usd",
        },
    )

    assert response.status_code == 502

    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        refreshed = await session.get(Booking, booking.id)
        assert refreshed is not None
        assert refreshed.stripe_payment_intent_id is None


@pytest.mark.anyio("asyncio")
async def test_create_payment_intent_missing_client_secret(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    booking = await _create_booking(app)

    payment_intent_create = Mock(return_value=SimpleNamespace(id="pi_456"))
    monkeypatch.setattr("stripe.PaymentIntent.create", payment_intent_create)

    response = await client.post(
        "/api/v1/platform/payments/intent",
        json={
            "booking_id": str(booking.id),
            "amount": 2222,
            "currency": "usd",
        },
    )

    assert response.status_code == 502

    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        refreshed = await session.get(Booking, booking.id)
        assert refreshed is not None
        assert refreshed.stripe_payment_intent_id is None


@pytest.mark.anyio("asyncio")
async def test_create_payment_intent_requires_currency_format(
    app: FastAPI, client: AsyncClient
) -> None:
    booking = await _create_booking(app)

    response = await client.post(
        "/api/v1/platform/payments/intent",
        json={
            "booking_id": str(booking.id),
            "amount": 1000,
            "currency": "US",
        },
    )

    assert response.status_code == 422


@pytest.mark.anyio("asyncio")
async def test_create_payment_intent_requires_stripe_configuration(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    booking = await _create_booking(app)

    # Reset API key to simulate missing configuration
    settings_override = app.dependency_overrides[get_settings]
    assert callable(settings_override)
    settings: Settings = settings_override()
    settings.stripe_api_key = None

    payment_intent_create = Mock()
    monkeypatch.setattr("stripe.PaymentIntent.create", payment_intent_create)

    response = await client.post(
        "/api/v1/platform/payments/intent",
        json={
            "booking_id": str(booking.id),
            "amount": 1234,
            "currency": "usd",
        },
    )

    assert response.status_code == 500
    payment_intent_create.assert_not_called()
