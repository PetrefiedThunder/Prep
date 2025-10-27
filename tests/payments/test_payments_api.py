"""Tests for the payments FastAPI router."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import AsyncGenerator
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from stripe.error import StripeError

from prep.database import get_db
from prep.models.orm import Base, User, UserRole
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


async def _create_host(app: FastAPI) -> User:
    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        host = User(
            email="host@example.com",
            full_name="Host Example",
            role=UserRole.HOST,
            is_active=True,
        )
        session.add(host)
        await session.commit()
        await session.refresh(host)
        return host


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
async def test_connect_endpoint_validates_payload(client: AsyncClient) -> None:
    response = await client.post("/payments/connect", json={"user_id": "not-a-uuid"})

    assert response.status_code == 422


@pytest.mark.anyio("asyncio")
async def test_connect_endpoint_user_not_found(client: AsyncClient) -> None:
    response = await client.post("/payments/connect", json={"user_id": str(uuid4())})

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.anyio("asyncio")
async def test_connect_endpoint_requires_host_role(
    app: FastAPI, client: AsyncClient
) -> None:
    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        customer = User(
            email="customer@example.com",
            full_name="Customer Example",
            role=UserRole.CUSTOMER,
            is_active=True,
        )
        session.add(customer)
        await session.commit()
        await session.refresh(customer)

    response = await client.post("/payments/connect", json={"user_id": str(customer.id)})

    assert response.status_code == 403
    assert response.json()["detail"] == "Only host accounts can connect payouts"


@pytest.mark.anyio("asyncio")
async def test_connect_endpoint_requires_stripe_configuration(
    app: FastAPI, client: AsyncClient
) -> None:
    host = await _create_host(app)

    app.dependency_overrides[get_settings] = lambda: Settings()

    response = await client.post("/payments/connect", json={"user_id": str(host.id)})

    assert response.status_code == 500
    assert response.json()["detail"] == "Stripe secret key is not configured"


@pytest.mark.anyio("asyncio")
async def test_connect_endpoint_handles_stripe_account_error(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = await _create_host(app)

    account_create = Mock(side_effect=StripeError(message="boom"))
    account_link_create = Mock()
    monkeypatch.setattr("stripe.Account.create", account_create)
    monkeypatch.setattr("stripe.AccountLink.create", account_link_create)

    response = await client.post("/payments/connect", json={"user_id": str(host.id)})

    assert response.status_code == 502
    assert (
        response.json()["detail"] == "Failed to initialize Stripe Connect onboarding"
    )

    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        refreshed = await session.get(User, host.id)
        assert refreshed is not None
        assert refreshed.stripe_account_id is None

    account_link_create.assert_not_called()


@pytest.mark.anyio("asyncio")
async def test_connect_endpoint_handles_stripe_account_link_error(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = await _create_host(app)

    account_create = Mock(return_value=SimpleNamespace(id="acct_123"))
    account_link_create = Mock(side_effect=StripeError(message="link error"))
    monkeypatch.setattr("stripe.Account.create", account_create)
    monkeypatch.setattr("stripe.AccountLink.create", account_link_create)

    response = await client.post("/payments/connect", json={"user_id": str(host.id)})

    assert response.status_code == 502
    assert (
        response.json()["detail"] == "Failed to initialize Stripe Connect onboarding"
    )

    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        refreshed = await session.get(User, host.id)
        assert refreshed is not None
        assert refreshed.stripe_account_id is None


@pytest.mark.anyio("asyncio")
async def test_connect_endpoint_reuses_existing_stripe_account(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = await _create_host(app)

    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        persisted = await session.get(User, host.id)
        assert persisted is not None
        persisted.stripe_account_id = "acct_existing"
        await session.commit()

    account_create = Mock()
    account_link_create = Mock(
        return_value=SimpleNamespace(url="https://connect.stripe.com/setup/s/example")
    )
    monkeypatch.setattr("stripe.Account.create", account_create)
    monkeypatch.setattr("stripe.AccountLink.create", account_link_create)

    response = await client.post("/payments/connect", json={"user_id": str(host.id)})

    assert response.status_code == 201
    assert response.json()["account_id"] == "acct_existing"

    account_create.assert_not_called()
    account_link_create.assert_called_once_with(
        account="acct_existing",
        refresh_url="https://example.com/refresh",
        return_url="https://example.com/return",
        type="account_onboarding",
    )
