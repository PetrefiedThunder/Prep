from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.api.integrations import router as integrations_router
from prep.auth import get_current_user
from prep.database.connection import get_db
from prep.models.orm import Base, Integration, IntegrationStatus, Kitchen, User, UserRole

pytestmark = pytest.mark.anyio("asyncio")


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
    application.include_router(integrations_router)
    application.dependency_overrides[get_db] = _override_get_db
    application.state.session_factory = session_factory

    try:
        yield application
    finally:
        application.dependency_overrides.clear()
        await engine.dispose()


@pytest.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


async def _create_user(app: FastAPI, *, role: UserRole, is_admin: bool = False) -> User:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        user = User(
            email=f"{uuid.uuid4()}@example.com",
            full_name="Integration Test User",
            hashed_password="hashed",
            role=role,
            is_admin=is_admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _create_kitchen(app: FastAPI, *, host: User) -> Kitchen:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        kitchen = Kitchen(
            host_id=host.id,
            name="Integration Kitchen",
            address="123 Integration Way",
        )
        session.add(kitchen)
        await session.commit()
        await session.refresh(kitchen)
        return kitchen


async def _create_integration(app: FastAPI, *, owner: User, kitchen: Kitchen) -> Integration:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        integration = Integration(
            user_id=owner.id,
            kitchen_id=kitchen.id,
            service_type="crm",
            vendor_name="Salesforce",
            auth_method="oauth2",
            sync_frequency="daily",
            status=IntegrationStatus.ACTIVE,
            metadata={"created_by": "test"},
        )
        session.add(integration)
        await session.commit()
        await session.refresh(integration)
        return integration


async def test_host_can_create_integration(app: FastAPI, client: AsyncClient) -> None:
    host = await _create_user(app, role=UserRole.HOST)
    kitchen = await _create_kitchen(app, host=host)

    async def _override_user() -> User:
        return host

    app.dependency_overrides[get_current_user] = _override_user

    payload = {
        "service_type": "accounting",
        "vendor_name": "QuickBooks",
        "auth_method": "oauth2",
        "sync_frequency": "hourly",
        "kitchen_id": str(kitchen.id),
        "metadata": {"region": "us-west"},
    }

    response = await client.post("/integrations/", json=payload)
    body = response.json()

    assert response.status_code == 201
    assert body["vendor_name"] == "QuickBooks"
    assert body["user_id"] == str(host.id)


async def test_renter_cannot_create_integration(app: FastAPI, client: AsyncClient) -> None:
    renter = await _create_user(app, role=UserRole.CUSTOMER)

    async def _override_user() -> User:
        return renter

    app.dependency_overrides[get_current_user] = _override_user

    payload = {
        "service_type": "crm",
        "vendor_name": "HubSpot",
        "auth_method": "api_key",
        "sync_frequency": "daily",
    }

    response = await client.post("/integrations/", json=payload)
    assert response.status_code == 403


async def test_admin_can_delete_other_integration(app: FastAPI, client: AsyncClient) -> None:
    host = await _create_user(app, role=UserRole.HOST)
    kitchen = await _create_kitchen(app, host=host)
    integration = await _create_integration(app, owner=host, kitchen=kitchen)
    admin = await _create_user(app, role=UserRole.ADMIN, is_admin=True)

    async def _override_user() -> User:
        return admin

    app.dependency_overrides[get_current_user] = _override_user

    response = await client.delete(f"/integrations/{integration.id}")
    assert response.status_code == 204

    # Verify the integration was removed
    session_factory = app.state.session_factory
    async with session_factory() as session:
        remaining = await session.get(Integration, integration.id)
        assert remaining is None
