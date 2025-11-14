from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from fnmatch import fnmatch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.cache import RedisProtocol, get_redis
from prep.database import get_db
from prep.mobile.api import router
from prep.models.orm import (
    Base,
    Booking,
    BookingStatus,
    Kitchen,
    KitchenMatchingProfile,
    User,
    UserMatchingPreference,
)

pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture()
async def app() -> AsyncGenerator[FastAPI, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    class DummyRedis(RedisProtocol):  # type: ignore[misc]
        def __init__(self) -> None:
            self._store: dict[str, tuple[float | None, str]] = {}

        async def get(self, key: str) -> str | None:
            entry = self._store.get(key)
            if not entry:
                return None
            expires, value = entry
            if expires is not None and expires < datetime.now(UTC).timestamp():
                self._store.pop(key, None)
                return None
            return value

        async def setex(self, key: str, ttl: int, value: str) -> None:
            expires_at = datetime.now(UTC).timestamp() + ttl if ttl else None
            self._store[key] = (expires_at, value)

        async def delete(self, *keys: str) -> int:
            removed = 0
            for key in keys:
                if key in self._store:
                    self._store.pop(key, None)
                    removed += 1
            return removed

        async def keys(self, pattern: str) -> list[str]:
            now = datetime.now(UTC).timestamp()
            matches: list[str] = []
            for key, (expires, _) in list(self._store.items()):
                if expires is not None and expires < now:
                    self._store.pop(key, None)
                    continue
                if fnmatch(key, pattern):
                    matches.append(key)
            return matches

    redis_backend = DummyRedis()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    async def _override_get_redis() -> RedisProtocol:
        return redis_backend

    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_redis] = _override_get_redis
    application.state.session_factory = session_factory

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


async def _seed_data(app: FastAPI) -> dict[str, User | Kitchen]:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        host = User(
            email="host@example.com",
            full_name="Host User",
            is_active=True,
            hashed_password="hostpass",
        )
        session.add(host)
        await session.flush()

        user = User(
            email="mobile@example.com",
            full_name="Mobile User",
            is_active=True,
            hashed_password="password123",
        )
        session.add(user)
        await session.flush()

        kitchen = Kitchen(
            id=uuid4(),
            name="Sunset Loft",
            description="Top floor kitchen",
            host_id=host.id,
            city="San Francisco",
            state="CA",
            hourly_rate=75,
            trust_score=4.5,
            moderation_status="approved",
            certification_status="approved",
            published=True,
        )
        session.add(kitchen)
        await session.flush()

        profile = KitchenMatchingProfile(
            kitchen_id=kitchen.id,
            equipment=["oven", "walk-in fridge"],
            cuisines=["Californian"],
            certifications=["health_department"],
            availability=["weekday"],
            latitude=37.7749,
            longitude=-122.4194,
        )
        session.add(profile)

        now = datetime.now(UTC)
        booking = Booking(
            host_id=host.id,
            customer_id=user.id,
            kitchen_id=kitchen.id,
            status=BookingStatus.CONFIRMED,
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=4),
            total_amount=150,
            platform_fee=15,
            host_payout_amount=135,
            source="seed",
        )
        session.add(booking)

        preferences = UserMatchingPreference(
            user_id=user.id,
            equipment=["oven"],
            preferred_cities=["san francisco"],
            preferred_states=["ca"],
            cuisines=["Californian"],
        )
        session.add(preferences)

        await session.commit()
        refreshed_user = await session.get(User, user.id)
        assert refreshed_user is not None
        assert refreshed_user.is_active is True
        assert refreshed_user.is_suspended is False
        return {"user": user, "kitchen": kitchen}


async def test_mobile_api_flow(app: FastAPI, client: AsyncClient) -> None:
    seeded = await _seed_data(app)

    login_payload = {
        "email": "mobile@example.com",
        "password": "password123",
        "device": {
            "device_id": "ios-device-1",
            "platform": "ios",
            "app_version": "2.0.0",
            "os_version": "16.4",
        },
    }
    login_response = await client.post("/api/v2/mobile/auth/login", json=login_payload)
    if login_response.status_code != 200:
        pytest.fail(
            "login failed: "
            f"{login_response.status_code} "
            f"{login_response.headers.get('content-type')} "
            f"{login_response.content}"
        )
    login_data = login_response.json()
    assert login_data["user_id"]
    assert login_data["tokens"]["access_token"]

    token = login_data["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nearby = await client.get(
        "/api/v2/mobile/kitchens/nearby",
        params={"latitude": 37.775, "longitude": -122.419, "radius_km": 5, "limit": 5},
        headers=headers,
    )
    assert nearby.status_code == 200
    nearby_payload = nearby.json()
    assert nearby_payload["items"]

    bookings = await client.get("/api/v2/mobile/bookings/upcoming", headers=headers)
    assert bookings.status_code == 200
    bookings_payload = bookings.json()
    assert bookings_payload["items"][0]["kitchen_name"] == "Sunset Loft"

    register_response = await client.post(
        "/api/v2/mobile/notifications/register",
        json={
            "device": login_payload["device"],
            "push_token": "push-token-abc",
            "locale": "en-US",
        },
        headers=headers,
    )
    assert register_response.status_code == 200

    sync_response = await client.get(
        "/api/v2/mobile/data/sync",
        params={"background_interval_minutes": 180},
        headers=headers,
    )
    assert sync_response.status_code == 200
    sync_payload = sync_response.json()
    assert sync_payload["kitchens"]

    upload_response = await client.post(
        "/api/v2/mobile/data/upload",
        json={
            "actions": [
                {
                    "action_type": "booking-note",
                    "payload": {"notes": "Arriving early"},
                    "recorded_at": datetime.now(UTC).isoformat(),
                }
            ]
        },
        headers=headers,
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["processed"] == 1

    cache_response = await client.get("/api/v2/mobile/cache/status", headers=headers)
    assert cache_response.status_code == 200
    assert cache_response.json()["has_sync_snapshot"] is True

    search_response = await client.get(
        "/api/v2/mobile/search/quick",
        params={"city": "San Francisco", "limit": 3},
        headers=headers,
    )
    assert search_response.status_code == 200
    assert search_response.json()["items"]

    quick_booking_payload = {
        "kitchen_id": str(seeded["kitchen"].id),
        "start_time": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "end_time": (datetime.now(UTC) + timedelta(days=2, hours=2)).isoformat(),
        "guests": 4,
        "notes": "Mobile booking",
    }
    booking_response = await client.post(
        "/api/v2/mobile/bookings/quick",
        json=quick_booking_payload,
        headers=headers,
    )
    assert booking_response.status_code == 200
    assert booking_response.json()["booking"]["role"] == "customer"

    detail_response = await client.get(
        f"/api/v2/mobile/kitchens/{seeded['kitchen'].id}/mobile",
        headers=headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["kitchen"]["name"] == "Sunset Loft"

    camera_response = await client.post(
        "/api/v2/mobile/camera/upload",
        json={
            "kitchen_id": str(seeded["kitchen"].id),
            "file_name": "prep.jpg",
            "content_type": "image/jpeg",
            "file_size_bytes": 2048,
        },
        headers=headers,
    )
    assert camera_response.status_code == 200

    biometric_key = "biometric-secret"
    bio_register = await client.post(
        "/api/v2/mobile/auth/biometric/register",
        json={"device": login_payload["device"], "biometric_key": biometric_key},
        headers=headers,
    )
    assert bio_register.status_code == 200

    bio_status = await client.get(
        "/api/v2/mobile/auth/biometric/status",
        params={"device_id": login_payload["device"]["device_id"]},
        headers=headers,
    )
    assert bio_status.status_code == 200
    assert bio_status.json()["registered"] is True

    bio_verify = await client.post(
        "/api/v2/mobile/auth/biometric/verify",
        json={"device_id": login_payload["device"]["device_id"], "signature": biometric_key},
    )
    assert bio_verify.status_code == 200
    assert bio_verify.json()["verified"] is True

    perf_metrics = await client.get("/api/v2/mobile/performance/metrics", headers=headers)
    assert perf_metrics.status_code == 200
    assert perf_metrics.json()["last_sync_at"] is not None

    perf_report = await client.post(
        "/api/v2/mobile/performance/report",
        json={
            "issue_type": "latency",
            "description": "App felt slow",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
        headers=headers,
    )
    assert perf_report.status_code == 200

    bandwidth = await client.get("/api/v2/mobile/bandwidth/estimate", headers=headers)
    assert bandwidth.status_code == 200
    assert bandwidth.json()["estimated_kbps"] > 0
