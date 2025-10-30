from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import AsyncGenerator
from uuid import UUID, uuid4

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy.ext.asyncio")

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.database import get_db
from prep.models.orm import (
    Base,
    Booking,
    BookingStatus,
    Kitchen,
    POSIntegration,
    POSOrder,
    POSTransaction,
    User,
    UserRole,
)
from prep.pos.api import router as pos_router

pytestmark = pytest.mark.anyio


@pytest.fixture()
async def app() -> AsyncGenerator[FastAPI, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    application = FastAPI()
    application.include_router(pos_router)
    application.dependency_overrides[get_db] = _get_db
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


async def _seed_records(app: FastAPI) -> tuple[UUID, UUID]:
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    kitchen_id = uuid4()
    toast_integration_id = uuid4()
    async with session_factory() as session:
        host = User(
            id=uuid4(),
            email="host@example.com",
            full_name="Host",
            hashed_password="secret",
            role=UserRole.HOST,
        )
        customer = User(
            id=uuid4(),
            email="guest@example.com",
            full_name="Guest",
            hashed_password="secret",
            role=UserRole.CUSTOMER,
        )
        kitchen = Kitchen(
            id=kitchen_id,
            host_id=host.id,
            name="Prep Kitchen",
            description="Test kitchen",
        )
        square_integration = POSIntegration(
            kitchen_id=kitchen_id,
            provider="square",
            refresh_token="refresh",
        )
        toast_integration = POSIntegration(
            id=toast_integration_id,
            kitchen_id=kitchen_id,
            provider="toast",
        )
        now = datetime.now(timezone.utc)
        booking = Booking(
            kitchen_id=kitchen_id,
            host_id=host.id,
            customer_id=customer.id,
            status=BookingStatus.COMPLETED,
            start_time=now - timedelta(hours=5),
            end_time=now - timedelta(hours=3),
            total_amount=Decimal("120"),
        )
        transaction = POSTransaction(
            integration=square_integration,
            kitchen_id=kitchen_id,
            provider="square",
            location_id="LOC-1",
            external_id="txn-1",
            amount=Decimal("95"),
            currency="USD",
            status="completed",
            occurred_at=now - timedelta(hours=4),
        )
        order = POSOrder(
            integration=toast_integration,
            kitchen_id=kitchen_id,
            provider="toast",
            external_id="order-1",
            total_amount=Decimal("25"),
            currency="USD",
            status="closed",
            closed_at=now - timedelta(hours=2),
        )
        session.add_all(
            [host, customer, kitchen, square_integration, toast_integration, booking, transaction, order]
        )
        await session.commit()
    return kitchen_id, toast_integration_id


async def test_get_pos_analytics_returns_metrics(app: FastAPI, client: AsyncClient) -> None:
    kitchen_id, _ = await _seed_records(app)
    response = await client.get(f"/api/v1/analytics/pos", params={"kitchen_id": str(kitchen_id), "hours": 24})
    assert response.status_code == 200
    payload = response.json()
    assert payload["kitchen_id"] == str(kitchen_id)
    assert payload["total_transactions"] == 1
    assert payload["total_sales"] == "120"
    assert payload["avg_ticket"] == "95"
    assert payload["sales_per_hour"] != "0"
    assert isinstance(payload["utilization_rate"], float)


async def test_toast_webhook_persists_order(app: FastAPI, client: AsyncClient) -> None:
    kitchen_id, toast_integration_id = await _seed_records(app)
    payload = {
        "orderGuid": "order-2",
        "status": "CLOSED",
        "orderNumber": "21",
        "closedDate": datetime.now(timezone.utc).isoformat(),
        "check": {"totals": {"grandTotal": {"amount": "1750"}, "currencyCode": "USD"}},
    }
    response = await client.post(
        f"/api/v1/webhooks/pos/toast/{toast_integration_id}",
        json=payload,
    )
    assert response.status_code == 204

    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    async with session_factory() as session:
        result = await session.execute(
            select(POSOrder).where(POSOrder.external_id == "order-2", POSOrder.kitchen_id == kitchen_id)
        )
        order = result.scalar_one()
        assert order.total_amount == Decimal("17.50")
        assert order.provider == "toast"
