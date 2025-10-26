"""Tests for the payments FastAPI router."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import AsyncGenerator
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
