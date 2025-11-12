from __future__ import annotations

from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

pytest.importorskip("sqlalchemy")
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.api.bookings import router as bookings_router
from prep.api.regulatory import router as regulatory_router
from prep.compliance.constants import BOOKING_COMPLIANCE_BANNER
from prep.database.connection import get_db
from prep.models.orm import Base, Kitchen, User
from prep.settings import get_settings

pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
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
    application.include_router(regulatory_router)
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


async def _create_user_and_kitchen(app: FastAPI) -> tuple[str, str]:
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
            name="Test Kitchen",
            compliance_status="compliant",
            city="San Francisco",
            state="CA",
        )
        session.add(kitchen)
        await session.commit()

        return str(customer.id), str(kitchen.id)


async def _post_booking(
    client: AsyncClient,
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


def _set_flag(monkeypatch: pytest.MonkeyPatch, value: bool | None) -> None:
    if value is None:
        monkeypatch.delenv("COMPLIANCE_CONTROLS_ENABLED", raising=False)
    else:
        monkeypatch.setenv("COMPLIANCE_CONTROLS_ENABLED", "1" if value else "0")
    get_settings.cache_clear()


async def test_booking_unrestricted_when_flag_disabled(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_flag(monkeypatch, False)
    user_id, kitchen_id = await _create_user_and_kitchen(app)

    saturday = datetime.now(UTC)
    while saturday.weekday() != 5:
        saturday += timedelta(days=1)
    start = saturday.replace(hour=7, minute=30, second=0, microsecond=0)
    end = saturday.replace(hour=14, minute=0, second=0, microsecond=0)

    response = await _post_booking(client, user_id, kitchen_id, start, end)
    assert response.status_code == 201


async def test_booking_restricted_to_weekdays_when_flag_enabled(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_flag(monkeypatch, True)
    user_id, kitchen_id = await _create_user_and_kitchen(app)

    saturday = datetime.now(UTC)
    while saturday.weekday() != 5:
        saturday += timedelta(days=1)
    start = saturday.replace(hour=9, minute=0, second=0, microsecond=0)
    end = saturday.replace(hour=10, minute=0, second=0, microsecond=0)

    response = await _post_booking(client, user_id, kitchen_id, start, end)
    assert response.status_code == 400
    assert BOOKING_COMPLIANCE_BANNER in response.json()["detail"]


async def test_booking_allows_valid_window_when_flag_enabled(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_flag(monkeypatch, True)
    user_id, kitchen_id = await _create_user_and_kitchen(app)

    monday = datetime.now(UTC)
    while monday.weekday() != 0:
        monday += timedelta(days=1)
    start = monday.replace(hour=9, minute=0, second=0, microsecond=0)
    end = monday.replace(hour=12, minute=0, second=0, microsecond=0)

    response = await _post_booking(client, user_id, kitchen_id, start, end)
    assert response.status_code == 201


async def test_compliance_banner_and_logging(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _set_flag(monkeypatch, True)
    caplog.set_level("INFO", logger="prep.api.regulatory")

    payload = {
        "kitchen_id": "123",
        "state": "CA",
        "city": "San Francisco",
        "kitchen_data": {"id": "123", "state": "CA", "city": "San Francisco"},
    }

    response = await client.post("/regulatory/compliance/check", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert body["booking_restrictions_banner"] == BOOKING_COMPLIANCE_BANNER
    assert any("Compliance decision issued" in record.getMessage() for record in caplog.records)


async def test_compliance_banner_omitted_when_flag_disabled(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_flag(monkeypatch, False)

    payload = {
        "kitchen_id": "123",
        "state": "CA",
        "city": "San Francisco",
        "kitchen_data": {"id": "123", "state": "CA", "city": "San Francisco"},
    }

    response = await client.post("/regulatory/compliance/check", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert "booking_restrictions_banner" not in body
