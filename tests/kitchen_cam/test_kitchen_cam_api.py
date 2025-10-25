from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.auth import get_current_user
from prep.cache import RedisProtocol, get_redis
from prep.database import get_db
from prep.kitchen_cam.api import router
from prep.models.orm import Base, Booking, BookingStatus, Kitchen, User


pytestmark = pytest.mark.anyio("asyncio")


class DummyRedis(RedisProtocol):  # type: ignore[misc]
    def __init__(self) -> None:
        self._store: dict[str, tuple[float | None, str]] = {}

    async def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if not entry:
            return None
        expires, value = entry
        if expires is not None and expires < datetime.now(timezone.utc).timestamp():
            self._store.pop(key, None)
            return None
        return value

    async def setex(self, key: str, ttl: int, value: str) -> None:
        expires_at = datetime.now(timezone.utc).timestamp() + ttl if ttl else None
        self._store[key] = (expires_at, value)


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
    application.include_router(router)
    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_redis] = _override_get_redis
    application.dependency_overrides[get_current_user] = _override_current_user
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

        operator = User(
            email="operator@example.com",
            full_name="Kitchen Operator",
            is_active=True,
            hashed_password="password123",
        )
        session.add(operator)
        await session.flush()

        kitchen = Kitchen(
            id=uuid4(),
            name="Downtown Prep Kitchen",
            description="High capacity kitchen",
            host_id=host.id,
            city="Seattle",
            state="WA",
            hourly_rate=125,
            trust_score=4.7,
            moderation_status="approved",
            certification_status="approved",
            published=True,
        )
        session.add(kitchen)
        await session.flush()

        now = datetime.now(timezone.utc)
        booking = Booking(
            host_id=host.id,
            customer_id=operator.id,
            kitchen_id=kitchen.id,
            status=BookingStatus.CONFIRMED,
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            total_amount=300,
            platform_fee=30,
            host_payout_amount=270,
        )
        session.add(booking)

        await session.commit()
        return {"user": operator, "kitchen": kitchen}


async def test_kitchen_cam_api_flow(app: FastAPI, client: AsyncClient) -> None:
    seeded = await _seed_data(app)
    user = seeded["user"]
    assert isinstance(user, User)

    def _current_user_override() -> User:
        return user

    app.dependency_overrides[get_current_user] = _current_user_override

    kitchen_id = str(seeded["kitchen"].id)

    status_response = await client.get(f"/api/v2/kitchen-cam/{kitchen_id}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["kitchen_id"] == kitchen_id
    assert status_data["status"] in {"offline", "privacy", "online"}

    heartbeat_payload = {
        "device_id": "cam-1",
        "status": "online",
        "uptime_seconds": 3600,
        "temperature_c": 42.5,
        "firmware_version": "1.2.3",
        "errors": [],
    }
    heartbeat_response = await client.post(
        f"/api/v2/kitchen-cam/{kitchen_id}/heartbeat",
        json=heartbeat_payload,
    )
    assert heartbeat_response.status_code == 200
    heartbeat_data = heartbeat_response.json()
    assert heartbeat_data["accepted"] is True

    lock_response = await client.post(
        f"/api/v2/kitchen-cam/{kitchen_id}/lock",
        json={"requested_by": "operator@example.com"},
    )
    assert lock_response.status_code == 200
    assert lock_response.json()["locked"] is True

    unlock_response = await client.post(
        f"/api/v2/kitchen-cam/{kitchen_id}/unlock",
        json={"requested_by": "operator@example.com"},
    )
    assert unlock_response.status_code == 200
    assert unlock_response.json()["locked"] is False

    usage_event = await client.post(
        f"/api/v2/kitchen-cam/{kitchen_id}/usage/event",
        json={"event_type": "door_open", "metadata": {"actor": "operator"}},
    )
    assert usage_event.status_code == 200
    history = await client.get(f"/api/v2/kitchen-cam/{kitchen_id}/usage/history")
    assert history.status_code == 200
    assert history.json()["events"]

    device_register = await client.post(
        f"/api/v2/kitchen-cam/{kitchen_id}/devices/register",
        json={
            "device_id": "lock-1",
            "device_type": "smart-lock",
            "capabilities": ["lock", "unlock"],
            "firmware_version": "5.4.0",
        },
    )
    assert device_register.status_code == 200
    assert device_register.json()["created"] is True

    device_update = await client.post(
        f"/api/v2/kitchen-cam/{kitchen_id}/devices/lock-1/update",
        json={"status": "active"},
    )
    assert device_update.status_code == 200
    assert device_update.json()["device"]["status"] == "active"

    devices = await client.get(f"/api/v2/kitchen-cam/{kitchen_id}/devices")
    assert devices.status_code == 200
    assert len(devices.json()["devices"]) == 1

    removal = await client.delete(f"/api/v2/kitchen-cam/{kitchen_id}/devices/lock-1")
    assert removal.status_code == 200
    assert removal.json()["removed"] is True

    privacy = await client.post(
        f"/api/v2/kitchen-cam/{kitchen_id}/privacy/mode",
        json={"mode": "on", "duration_minutes": 30},
    )
    assert privacy.status_code == 200
    privacy_status = await client.get(f"/api/v2/kitchen-cam/{kitchen_id}/privacy/status")
    assert privacy_status.status_code == 200
    assert privacy_status.json()["mode"] == "on"

    expire = await client.post(
        f"/api/v2/kitchen-cam/{kitchen_id}/data/expire",
        json={"before": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()},
    )
    assert expire.status_code == 200
    assert expire.json()["scheduled"] is True

    policies = await client.get("/api/v2/kitchen-cam/privacy/policies")
    assert policies.status_code == 200
    assert len(policies.json()["items"]) >= 2

    cameras = await client.get(f"/api/v2/kitchen-cam/{kitchen_id}/cameras")
    assert cameras.status_code == 200
    assert len(cameras.json()["items"]) >= 2

    snapshot = await client.get(
        f"/api/v2/kitchen-cam/{kitchen_id}/cameras/primary/snapshot"
    )
    assert snapshot.status_code == 200

    record = await client.post(
        f"/api/v2/kitchen-cam/{kitchen_id}/cameras/primary/record",
        json={"duration_seconds": 120},
    )
    assert record.status_code == 200
    assert record.json()["recording_id"]

    occupancy = await client.get(f"/api/v2/kitchen-cam/{kitchen_id}/occupancy")
    assert occupancy.status_code == 200
    assert occupancy.json()["is_occupied"] is True

    live = await client.get(f"/api/v2/kitchen-cam/{kitchen_id}/live")
    assert live.status_code == 200

    schedule = await client.get(f"/api/v2/kitchen-cam/{kitchen_id}/schedule")
    assert schedule.status_code == 200
    assert schedule.json()["items"]

    stats = await client.get(f"/api/v2/kitchen-cam/{kitchen_id}/usage")
    assert stats.status_code == 200
