from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.admin.api import router
from prep.admin.dependencies import get_current_admin
from prep.database import get_db
from prep.models.admin import AdminUser
from prep.models.db import (
    Base,
    CertificationDocument,
    CertificationReviewStatus,
    Kitchen,
    ModerationStatus,
    User,
    UserRole,
)


@pytest.fixture()
async def app() -> AsyncGenerator[FastAPI, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    admin = AdminUser(
        id=uuid4(),
        email="admin@example.com",
        full_name="Prep Admin",
        permissions=["admin:full"],
    )

    async def _override_get_current_admin() -> AdminUser:
        return admin

    application = FastAPI()
    application.include_router(router)
    application.state.session_factory = session_factory
    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_current_admin] = _override_get_current_admin

    try:
        yield application
    finally:
        await engine.dispose()


@pytest.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


async def _seed_user(session: AsyncSession, **kwargs) -> User:
    user = User(
        email=kwargs.get("email", "host@example.com"),
        full_name=kwargs.get("full_name", "Jordan Host"),
        hashed_password="hashed",
        role=kwargs.get("role", UserRole.HOST),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _seed_kitchen(session: AsyncSession, owner: User, **kwargs) -> Kitchen:
    kitchen = Kitchen(
        name=kwargs.get("name", "Sunset Loft"),
        owner_id=owner.id,
        location=kwargs.get("location", "San Francisco"),
        description=kwargs.get("description", ""),
        trust_score=kwargs.get("trust_score"),
        hourly_rate=kwargs.get("hourly_rate"),
        certification_status=kwargs.get(
            "certification_status", CertificationReviewStatus.PENDING
        ),
        moderation_status=kwargs.get("moderation_status", ModerationStatus.PENDING),
        submitted_at=kwargs.get("submitted_at", datetime.now(timezone.utc)),
    )
    session.add(kitchen)
    await session.flush()
    return kitchen


async def _seed_certification(session: AsyncSession, kitchen: Kitchen, **kwargs) -> CertificationDocument:
    certification = CertificationDocument(
        kitchen_id=kitchen.id,
        document_type=kwargs.get("document_type", "health_department"),
        document_url=kwargs.get("document_url", "https://example.com/cert.pdf"),
        status=kwargs.get("status", CertificationReviewStatus.PENDING),
        submitted_at=kwargs.get("submitted_at", datetime.now(timezone.utc)),
        expires_at=kwargs.get("expires_at"),
    )
    session.add(certification)
    await session.flush()
    return certification


@pytest.mark.anyio
async def test_list_pending_kitchens(client: AsyncClient, app: FastAPI) -> None:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        owner = await _seed_user(session)
        await _seed_kitchen(session, owner, name="Pending Kitchen")
        approved_owner = await _seed_user(session, email="approved@example.com")
        await _seed_kitchen(
            session,
            approved_owner,
            name="Approved Kitchen",
            moderation_status=ModerationStatus.APPROVED,
        )
        await session.commit()

    response = await client.get("/api/v1/admin/kitchens/pending")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    assert payload["items"][0]["name"] == "Pending Kitchen"


@pytest.mark.anyio
async def test_moderate_kitchen_approve(client: AsyncClient, app: FastAPI) -> None:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        owner = await _seed_user(session)
        kitchen = await _seed_kitchen(session, owner)
        await session.commit()
        kitchen_id = kitchen.id

    response = await client.post(
        f"/api/v1/admin/kitchens/{kitchen_id}/moderate",
        json={"action": "approve"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["kitchen"]["moderation_status"] == ModerationStatus.APPROVED.value

    async with session_factory() as session:
        refreshed = await session.get(Kitchen, kitchen_id)
        assert refreshed.moderation_status == ModerationStatus.APPROVED


@pytest.mark.anyio
async def test_certification_verification_flow(client: AsyncClient, app: FastAPI) -> None:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        owner = await _seed_user(session)
        kitchen = await _seed_kitchen(session, owner)
        certification = await _seed_certification(session, kitchen)
        await session.commit()
        certification_id = certification.id

    list_response = await client.get("/api/v1/admin/certifications/pending")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["pagination"]["total"] == 1

    verify_response = await client.post(
        f"/api/v1/admin/certifications/{certification_id}/verify",
        json={"approve": True},
    )
    assert verify_response.status_code == 200
    data = verify_response.json()
    assert data["certification"]["status"] == CertificationReviewStatus.APPROVED.value


@pytest.mark.anyio
async def test_user_listing_and_suspension(client: AsyncClient, app: FastAPI) -> None:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        active_user = await _seed_user(session, email="active@example.com", full_name="Active User")
        suspended_user = await _seed_user(
            session,
            email="suspended@example.com",
            full_name="Suspended User",
        )
        suspended_user.is_suspended = True
        await session.commit()
        active_id = active_user.id

    list_response = await client.get("/api/v1/admin/users")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["pagination"]["total"] == 1

    suspend_response = await client.post(
        f"/api/v1/admin/users/{active_id}/suspend",
        json={"reason": "Violation"},
    )
    assert suspend_response.status_code == 200
    body = suspend_response.json()
    assert body["is_suspended"] is True
    assert body["suspension_reason"] == "Violation"


@pytest.mark.anyio
async def test_stats_endpoints(client: AsyncClient, app: FastAPI) -> None:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        admin_user = await _seed_user(session, email="admin@example.com", role=UserRole.ADMIN)
        owner = await _seed_user(session)
        kitchen = await _seed_kitchen(session, owner)
        kitchen.moderation_status = ModerationStatus.APPROVED
        kitchen.moderated_at = datetime.now(timezone.utc)
        certification = await _seed_certification(
            session,
            kitchen,
            status=CertificationReviewStatus.APPROVED,
            expires_at=datetime.now(timezone.utc) + timedelta(days=10),
        )
        certification.reviewer_id = admin_user.id
        await session.commit()

    kitchen_stats = await client.get("/api/v1/admin/kitchens/stats")
    assert kitchen_stats.status_code == 200
    assert kitchen_stats.json()["approved"] == 1

    certification_stats = await client.get("/api/v1/admin/certifications/stats")
    assert certification_stats.status_code == 200
    assert certification_stats.json()["approved"] == 1

    user_stats = await client.get("/api/v1/admin/users/stats")
    assert user_stats.status_code == 200
    assert user_stats.json()["admins"] >= 1
