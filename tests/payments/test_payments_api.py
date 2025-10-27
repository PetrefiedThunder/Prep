"""Tests for the payments FastAPI router."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import AsyncGenerator
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from stripe.error import SignatureVerificationError

from prep.database import get_db
from prep.models.orm import Base, Booking, Kitchen, StripeWebhookEvent, User, UserRole
from prep.payments.api import router as payments_router
from prep.settings import Settings, get_settings


class _AsyncSessionFactory:
    """Helper to expose session factory through FastAPI state."""

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._factory() as session:
            yield session


@pytest.fixture()
async def app() -> AsyncGenerator[FastAPI, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    state_factory = _AsyncSessionFactory(session_factory)

    application = FastAPI()
    application.include_router(payments_router)
    application.state.sessions = state_factory

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with state_factory.session() as session:
            yield session

    settings = Settings()
    settings.stripe_secret_key = "sk_test_123"
    settings.stripe_connect_refresh_url = "https://example.com/refresh"
    settings.stripe_connect_return_url = "https://example.com/return"
    settings.stripe_webhook_secret = "whsec_test"

    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_settings] = lambda: settings

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


async def _create_user(app: FastAPI, *, role: UserRole, email: str) -> User:
    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        user = User(
            email=email,
            full_name="User Example",
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _create_host(app: FastAPI) -> User:
    return await _create_user(app, role=UserRole.HOST, email="host@example.com")


async def _create_customer(app: FastAPI) -> User:
    return await _create_user(app, role=UserRole.CUSTOMER, email="customer@example.com")


async def _create_booking(
    app: FastAPI, *, host: User, customer: User, payment_intent_id: str
) -> Booking:
    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        kitchen = Kitchen(
            host_id=host.id,
            name="Test Kitchen",
            published=True,
        )
        booking = Booking(
            kitchen=kitchen,
            host_id=host.id,
            customer_id=customer.id,
            start_time=datetime.now(UTC) + timedelta(days=1),
            end_time=datetime.now(UTC) + timedelta(days=1, hours=2),
            payment_intent_id=payment_intent_id,
        )
        session.add_all([kitchen, booking])
        await session.commit()
        await session.refresh(booking)
        return booking


@pytest.mark.anyio("asyncio")
async def test_connect_endpoint_creates_stripe_account(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = await _create_host(app)

    account_create = Mock(return_value=SimpleNamespace(id="acct_123"))
    account_link_create = Mock(
        return_value={"url": "https://connect.stripe.com/setup/s/example"}
    )
    monkeypatch.setattr("stripe.Account.create", account_create)
    monkeypatch.setattr("stripe.AccountLink.create", account_link_create)

    response = await client.post(
        "/payments/connect",
        json={"user_id": str(host.id)},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["account_id"] == "acct_123"
    assert data["onboarding_url"].startswith("https://connect.stripe.com/setup")

    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        refreshed = await session.get(User, host.id)
        assert refreshed is not None
        assert refreshed.stripe_account_id == "acct_123"

    account_create.assert_called_once_with(type="custom")
    account_link_create.assert_called_once()


@pytest.mark.anyio("asyncio")
async def test_webhook_requires_signature_header(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "stripe.Webhook.construct_event", Mock(return_value={"id": "evt_1"})
    )

    response = await client.post("/payments/webhook", content=b"{}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing Stripe signature"


@pytest.mark.anyio("asyncio")
async def test_webhook_rejects_invalid_signature(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(*args, **kwargs):
        raise SignatureVerificationError("invalid", "body")

    monkeypatch.setattr("stripe.Webhook.construct_event", _raise)

    response = await client.post(
        "/payments/webhook",
        content=b"{}",
        headers={"stripe-signature": "sig_123"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Stripe signature"


@pytest.mark.anyio("asyncio")
async def test_webhook_marks_booking_paid(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = await _create_host(app)
    customer = await _create_customer(app)
    booking = await _create_booking(app, host=host, customer=customer, payment_intent_id="pi_123")

    event_payload = {
        "id": "evt_123",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_123"}},
    }
    monkeypatch.setattr("stripe.Webhook.construct_event", Mock(return_value=event_payload))

    response = await client.post(
        "/payments/webhook",
        content=b"{}",
        headers={"stripe-signature": "sig_123"},
    )

    assert response.status_code == 204

    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        refreshed = await session.get(Booking, booking.id)
        assert refreshed is not None
        assert refreshed.paid is True

        events = await session.scalars(select(StripeWebhookEvent))
        assert [event.event_id for event in events] == ["evt_123"]


@pytest.mark.anyio("asyncio")
async def test_webhook_is_idempotent(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = await _create_host(app)
    customer = await _create_customer(app)
    booking = await _create_booking(app, host=host, customer=customer, payment_intent_id="pi_456")

    event_payload = {
        "id": "evt_456",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_456"}},
    }
    construct_event = Mock(return_value=event_payload)
    monkeypatch.setattr("stripe.Webhook.construct_event", construct_event)

    for _ in range(2):
        response = await client.post(
            "/payments/webhook",
            content=b"{}",
            headers={"stripe-signature": "sig_123"},
        )
        assert response.status_code == 204

    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        refreshed = await session.get(Booking, booking.id)
        assert refreshed is not None
        assert refreshed.paid is True

        events = await session.scalars(select(StripeWebhookEvent))
        assert [event.event_id for event in events] == ["evt_456"]
