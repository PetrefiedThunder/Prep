"""Tests for the delivery orchestration API."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.api.deliveries import router as deliveries_router
from prep.api.orders import router as orders_router
from prep.database import get_db
from prep.delivery.schemas import DeliveryProvider
from prep.models.orm import Base, DeliveryComplianceEvent, DeliveryOrder, DeliveryStatus
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
    application.include_router(deliveries_router)
    application.include_router(orders_router)
    application.state.sessions = state_factory

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with state_factory.session() as session:
            yield session

    settings = Settings()
    settings.use_fixtures = True
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


@pytest.mark.anyio("asyncio")
async def test_create_delivery_persists_order(app: FastAPI, client: AsyncClient) -> None:
    payload = {
        "external_order_id": "order-123",
        "provider": DeliveryProvider.DOORDASH.value,
        "pickup": {
            "name": "Prep Kitchen",
            "address": "123 Prep St",
            "city": "Austin",
        },
        "dropoff": {
            "name": "Customer",
            "address": "987 Flavor Ave",
            "city": "Austin",
        },
        "items": ["Box"],
    }

    response = await client.post("/deliveries/create", json=payload)
    assert response.status_code == 201
    data = response.json()["delivery"]
    assert data["external_order_id"] == "order-123"
    assert data["provider"] == DeliveryProvider.DOORDASH.value
    assert data["status"] == DeliveryStatus.CREATED.value

    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        saved = await session.scalar(
            select(DeliveryOrder).where(DeliveryOrder.external_order_id == "order-123")
        )
        assert saved is not None
        assert saved.provider == DeliveryProvider.DOORDASH


@pytest.mark.anyio("asyncio")
async def test_status_webhook_updates_delivery_and_logs_compliance(
    app: FastAPI, client: AsyncClient
) -> None:
    payload = {
        "external_order_id": "order-456",
        "provider": DeliveryProvider.UBER.value,
        "pickup": {"name": "Kitchen", "address": "123 Main"},
        "dropoff": {"name": "Guest", "address": "789 Elm"},
    }
    await client.post("/deliveries/create", json=payload)

    update_payload = {
        "provider": DeliveryProvider.UBER.value,
        "external_order_id": "order-456",
        "status": "delivered",
        "courier_name": "Sam Courier",
        "courier_phone": "+1234567890",
        "proof_photo_url": "https://example.com/photo.jpg",
        "proof_signature": "signed",
        "occurred_at": datetime.now(UTC).isoformat(),
    }

    response = await client.post("/deliveries/status", json=update_payload)
    assert response.status_code == 202

    state_factory: _AsyncSessionFactory = app.state.sessions
    async with state_factory.session() as session:
        delivery = await session.scalar(
            select(DeliveryOrder).where(DeliveryOrder.external_order_id == "order-456")
        )
        assert delivery is not None
        assert delivery.status == DeliveryStatus.DELIVERED
        assert delivery.proof_photo_url == "https://example.com/photo.jpg"
        assert delivery.proof_signature == "signed"
        compliance_event = await session.scalar(
            select(DeliveryComplianceEvent).where(
                DeliveryComplianceEvent.delivery_id == delivery.id
            )
        )
        assert compliance_event is not None
        assert compliance_event.courier_identity == "Sam Courier"


@pytest.mark.anyio("asyncio")
async def test_orders_endpoint_merges_providers(app: FastAPI, client: AsyncClient) -> None:
    dd_payload = {
        "external_order_id": "order-dd",
        "provider": DeliveryProvider.DOORDASH.value,
        "pickup": {"name": "Prep Kitchen", "address": "123 Prep"},
        "dropoff": {"name": "Customer", "address": "999 Grove"},
    }
    uber_payload = {
        "external_order_id": "order-uber",
        "provider": DeliveryProvider.UBER.value,
        "pickup": {"name": "Prep Kitchen", "address": "456 Prep"},
        "dropoff": {"name": "Customer", "address": "111 Grove"},
    }

    await client.post("/deliveries/create", json=dd_payload)
    await client.post("/deliveries/create", json=uber_payload)

    await client.post(
        "/deliveries/status",
        json={
            "provider": DeliveryProvider.DOORDASH.value,
            "external_order_id": "order-dd",
            "status": "enroute_dropoff",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    await client.post(
        "/deliveries/status",
        json={
            "provider": DeliveryProvider.UBER.value,
            "external_order_id": "order-uber",
            "status": "courier_en_route_to_pickup",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )

    response = await client.get("/orders")
    assert response.status_code == 200
    body = response.json()
    assert body["connectors"][DeliveryProvider.DOORDASH.value] == "authenticated"
    assert body["connectors"][DeliveryProvider.UBER.value] == "authenticated"
    assert body["reconciliation_accuracy"] == 0
    orders = {order["external_order_id"]: order for order in body["orders"]}
    assert orders["order-dd"]["status"] == DeliveryStatus.IN_TRANSIT.value
    assert orders["order-uber"]["status"] == DeliveryStatus.DISPATCHED.value
