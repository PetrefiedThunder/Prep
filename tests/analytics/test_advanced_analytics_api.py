from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from fnmatch import fnmatch
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.analytics.advanced_api import router as analytics_router
from prep.analytics.advanced_service import AdvancedAnalyticsService
from prep.auth import get_current_user
from prep.cache import RedisProtocol, get_redis
from prep.database import get_db
from prep.kitchen_cam.service import KitchenCamService
from prep.models.orm import Base, Booking, BookingStatus, Kitchen, Review, User

pytestmark = pytest.mark.anyio("asyncio")


class DummyRedis(RedisProtocol):  # type: ignore[misc]
    def __init__(self) -> None:
        self._store: dict[str, tuple[float | None, str]] = {}

    async def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at is not None and expires_at < datetime.now(tz=UTC).timestamp():
            self._store.pop(key, None)
            return None
        return value

    async def setex(self, key: str, ttl: int, value: str) -> None:
        expires_at = datetime.now(tz=UTC).timestamp() + ttl if ttl else None
        self._store[key] = (expires_at, value)

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self._store:
                self._store.pop(key, None)
                removed += 1
        return removed

    async def keys(self, pattern: str) -> list[str]:
        now = datetime.now(tz=UTC).timestamp()
        matches: list[str] = []
        for key, (expires_at, _) in list(self._store.items()):
            if expires_at is not None and expires_at < now:
                self._store.pop(key, None)
                continue
            if fnmatch(key, pattern):
                matches.append(key)
        return matches


@pytest.fixture()
async def app() -> AsyncGenerator[FastAPI, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    redis_backend = DummyRedis()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    async def _override_get_redis() -> RedisProtocol:
        return redis_backend

    async def _override_current_user() -> User:
        raise RuntimeError("current user override must be set in tests")

    application = FastAPI()
    application.include_router(analytics_router)
    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_redis] = _override_get_redis
    application.dependency_overrides[get_current_user] = _override_current_user
    application.state.session_factory = session_factory
    application.state.redis_backend = redis_backend

    try:
        yield application
    finally:
        await engine.dispose()


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


async def _seed_data(app: FastAPI) -> dict[str, Any]:
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    async with session_factory() as session:
        admin = User(
            email="admin@example.com",
            full_name="Admin User",
            hashed_password="hashed",
            is_active=True,
        )
        guest = User(
            email="guest@example.com",
            full_name="Guest User",
            hashed_password="hashed",
            is_active=True,
        )
        session.add_all([admin, guest])
        await session.flush()

        kitchen = Kitchen(
            id=uuid4(),
            name="Downtown Kitchen",
            host_id=admin.id,
            city="Seattle",
            state="WA",
            hourly_rate=150,
            moderation_status="approved",
            certification_status="approved",
            published=True,
        )
        session.add(kitchen)
        await session.flush()

        now = datetime.now(tz=UTC)
        bookings = [
            Booking(
                host_id=admin.id,
                customer_id=guest.id,
                kitchen_id=kitchen.id,
                status=BookingStatus.COMPLETED,
                start_time=now - timedelta(days=10, hours=4),
                end_time=now - timedelta(days=10, hours=1),
                total_amount=320,
            ),
            Booking(
                host_id=admin.id,
                customer_id=guest.id,
                kitchen_id=kitchen.id,
                status=BookingStatus.CONFIRMED,
                start_time=now - timedelta(days=2, hours=3),
                end_time=now - timedelta(days=2, hours=1),
                total_amount=280,
            ),
            Booking(
                host_id=admin.id,
                customer_id=guest.id,
                kitchen_id=kitchen.id,
                status=BookingStatus.CONFIRMED,
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=2),
                total_amount=350,
            ),
        ]
        session.add_all(bookings)
        await session.flush()

        review = Review(
            booking_id=bookings[0].id,
            kitchen_id=kitchen.id,
            host_id=admin.id,
            customer_id=guest.id,
            rating=4.6,
            equipment_rating=4.8,
            cleanliness_rating=4.5,
            communication_rating=4.7,
            value_rating=4.4,
            comment="Great experience",
        )
        session.add(review)
        await session.commit()

    redis_backend: DummyRedis = app.state.redis_backend
    usage_events = [
        {
            "event_type": "temperature_alert",
            "recorded_at": (datetime.now(tz=UTC) - timedelta(hours=3)).isoformat(),
            "metadata": {"equipment": "ovens", "cost": 45},
        },
        {
            "event_type": "filter_replacement",
            "recorded_at": (datetime.now(tz=UTC) - timedelta(days=1)).isoformat(),
            "metadata": {"equipment": "vents", "resolved": True},
        },
    ]
    await redis_backend.setex(
        f"kitchen_cam:usage:{kitchen.id}",
        KitchenCamService.USAGE_EVENT_TTL,
        json.dumps(usage_events),
    )
    await redis_backend.setex(
        f"kitchen_cam:last_heartbeat:{kitchen.id}",
        KitchenCamService.HEARTBEAT_TTL,
        json.dumps(
            {
                "recorded_at": (datetime.now(tz=UTC) - timedelta(minutes=90)).isoformat(),
            }
        ),
    )

    return {"admin": admin, "guest": guest, "kitchen": kitchen, "usage_events": usage_events}


async def test_predictive_maintenance_endpoint(app: FastAPI, client: AsyncClient) -> None:
    seeded = await _seed_data(app)
    admin: User = seeded["admin"]

    app.dependency_overrides[get_current_user] = lambda: admin

    response = await client.get("/api/v2/analytics/maintenance/predict")
    assert response.status_code == 200
    payload = response.json()
    assert payload["predictions"]
    assert payload["predictions"][0]["confidence"] <= 1

    redis_backend: DummyRedis = app.state.redis_backend
    notifications = await redis_backend.get(AdvancedAnalyticsService.NOTIFICATION_KEY)
    assert notifications is not None


async def test_usage_forecast_endpoint(app: FastAPI, client: AsyncClient) -> None:
    seeded = await _seed_data(app)
    admin: User = seeded["admin"]
    kitchen_id = str(seeded["kitchen"].id)

    app.dependency_overrides[get_current_user] = lambda: admin

    response = await client.post(
        "/api/v2/analytics/usage/forecast",
        json={"kitchen_id": kitchen_id, "horizon_days": 5},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["forecast"]
    assert len(payload["forecast"]) == 5
    assert all(0 <= point["confidence"] <= 1 for point in payload["forecast"])


async def test_revenue_forecast_endpoint(app: FastAPI, client: AsyncClient) -> None:
    seeded = await _seed_data(app)
    admin: User = seeded["admin"]

    app.dependency_overrides[get_current_user] = lambda: admin

    response = await client.post(
        "/api/v2/analytics/revenue/forecast",
        json={"horizon_months": 3},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["forecast"]
    assert len(payload["forecast"]) == 3
    assert all("projected_revenue" in point for point in payload["forecast"])


async def test_behavior_prediction_endpoint(app: FastAPI, client: AsyncClient) -> None:
    seeded = await _seed_data(app)
    admin: User = seeded["admin"]
    guest: User = seeded["guest"]

    app.dependency_overrides[get_current_user] = lambda: admin

    response = await client.post(
        "/api/v2/analytics/behavior/predict",
        json={"user_id": str(guest.id)},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["prediction"]["user_id"] == str(guest.id)
    assert 0 <= payload["prediction"]["retention_probability"] <= 1
