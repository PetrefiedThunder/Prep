from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

pytest.importorskip("sqlalchemy.ext.asyncio")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from jobs.reconciliation_engine import run_pos_reconciliation
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
from prep.settings import get_settings

pytestmark = pytest.mark.anyio


class StubS3Client:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def put_object(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)

    def close(self) -> None:
        pass


class StubCache:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self.store:
                removed += 1
                self.store.pop(key, None)
        return removed

    async def keys(self, pattern: str) -> list[str]:
        return list(self.store.keys())


@pytest.fixture()
async def session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


async def _seed_data(session_factory: async_sessionmaker[AsyncSession]) -> UUID:
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
        kitchen = Kitchen(id=uuid4(), host_id=host.id, name="Kitchen")
        integration = POSIntegration(kitchen_id=kitchen.id, provider="square", refresh_token="r1")
        now = datetime.now(UTC)
        booking = Booking(
            kitchen_id=kitchen.id,
            host_id=host.id,
            customer_id=customer.id,
            status=BookingStatus.COMPLETED,
            start_time=now - timedelta(hours=3),
            end_time=now - timedelta(hours=1),
            total_amount=Decimal("200"),
        )
        transaction = POSTransaction(
            integration=integration,
            kitchen_id=kitchen.id,
            provider="square",
            external_id="txn-1",
            amount=Decimal("150"),
            currency="USD",
            status="completed",
            occurred_at=now - timedelta(hours=2),
        )
        order = POSOrder(
            integration=integration,
            kitchen_id=kitchen.id,
            provider="square",
            external_id="order-1",
            total_amount=Decimal("25"),
            currency="USD",
            status="closed",
            closed_at=now - timedelta(hours=2),
        )
        session.add_all([host, customer, kitchen, integration, booking, transaction, order])
        await session.commit()
        return kitchen.id


async def test_run_pos_reconciliation_generates_report(
    session_factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    kitchen_id = await _seed_data(session_factory)
    monkeypatch.setenv("POS_LEDGER_BUCKET", "test-ledger")
    get_settings.cache_clear()

    stub_s3 = StubS3Client()
    cache = StubCache()
    start = datetime.now(UTC) - timedelta(hours=4)
    end = datetime.now(UTC)

    report = await run_pos_reconciliation(
        start=start,
        end=end,
        session_factory=session_factory,
        s3_client=stub_s3,
        cache=cache,
    )

    assert report.entries
    entry = report.entries[0]
    assert entry.kitchen_id == kitchen_id
    assert entry.booking_total == Decimal("200")
    assert entry.pos_transaction_total == Decimal("150")
    assert entry.pos_order_total == Decimal("25")
    assert stub_s3.calls
    assert report.s3_object_key is not None

    get_settings.cache_clear()
