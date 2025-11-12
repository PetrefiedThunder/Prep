from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from prep.admin.api import router as admin_router
from prep.admin.dependencies import get_current_admin
from prep.database import get_db as core_get_db
from prep.database.connection import get_db as connection_get_db
from prep.models.admin import AdminUser
from prep.models.orm import (
    Base,
    CertificationDocument,
    CertificationReviewStatus,
    Kitchen,
    ModerationStatus,
    User,
    UserRole,
)

pytestmark = pytest.mark.anyio("asyncio")


@dataclass
class AppContext:
    app: FastAPI
    session_factory: async_sessionmaker[AsyncSession]
    admin_user: AdminUser


@pytest.fixture
async def admin_app_context() -> AppContext:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    app = FastAPI()
    app.include_router(admin_router)

    admin_id = uuid4()
    admin_user = AdminUser(
        id=admin_id,
        email="admin@example.com",
        full_name="Admin User",
        permissions=["moderate", "certify"],
    )

    async def _get_db() -> AsyncSession:
        async with session_factory() as session:
            yield session

    async def _get_admin() -> AdminUser:
        return admin_user

    app.dependency_overrides[core_get_db] = _get_db
    app.dependency_overrides[connection_get_db] = _get_db
    app.dependency_overrides[get_current_admin] = _get_admin

    async with session_factory() as session:
        admin_record = User(
            id=admin_id,
            email=admin_user.email,
            full_name=admin_user.full_name,
            role=UserRole.ADMIN,
            is_active=True,
            is_admin=True,
        )
        session.add(admin_record)
        await session.commit()

    yield AppContext(app=app, session_factory=session_factory, admin_user=admin_user)

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.anyio
async def test_admin_moderation_and_certification_flow(admin_app_context: AppContext) -> None:
    context = admin_app_context

    host_id = uuid4()
    async with context.session_factory() as session:
        host = User(
            id=host_id,
            email="host@example.com",
            full_name="Host Example",
            role=UserRole.HOST,
            is_active=True,
        )
        renter = User(
            email="renter@example.com",
            full_name="Renter Example",
            role=UserRole.CUSTOMER,
            is_active=True,
        )
        kitchen = Kitchen(
            host=host,
            name="Moderation Kitchen",
            description="Test kitchen awaiting moderation",
            address="123 Main St",
            location="Austin",
            city="Austin",
            state="TX",
            hourly_rate=Decimal("75.00"),
            trust_score=4.8,
            moderation_status=ModerationStatus.PENDING,
            certification_status=CertificationReviewStatus.PENDING,
            compliance_status="compliant",
        )
        certification = CertificationDocument(
            kitchen=kitchen,
            document_type="health_permit",
            document_url="https://example.com/permit.pdf",
            status=CertificationReviewStatus.PENDING,
        )
        session.add_all([host, renter, kitchen, certification])
        await session.commit()

        kitchen_id: UUID = kitchen.id
        certification_id: UUID = certification.id
        renter_id: UUID = renter.id

    transport = ASGITransport(app=context.app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/admin/kitchens/pending")
        assert response.status_code == 200
        kitchens_payload = response.json()
        assert kitchens_payload["pagination"]["total"] == 1
        assert kitchens_payload["items"][0]["name"] == "Moderation Kitchen"

        detail_response = await client.get(f"/api/v1/admin/kitchens/{kitchen_id}")
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        assert detail_payload["owner_email"] == "host@example.com"

        moderation_response = await client.post(
            f"/api/v1/admin/kitchens/{kitchen_id}/moderate",
            json={"action": "approve"},
        )
        assert moderation_response.status_code == 200
        moderation_payload = moderation_response.json()
        assert moderation_payload["message"] == "Kitchen approved"
        assert moderation_payload["kitchen"]["moderation_status"] == "approved"

        cert_response = await client.post(
            f"/api/v1/admin/certifications/{certification_id}/verify",
            json={"approve": True},
        )
        assert cert_response.status_code == 200
        cert_payload = cert_response.json()
        assert cert_payload["certification"]["status"] == "approved"

        stats_response = await client.get("/api/v1/admin/metrics/kitchens")
        assert stats_response.status_code == 200
        stats_payload = stats_response.json()
        assert stats_payload["approved"] >= 1

        cert_stats_response = await client.get("/api/v1/admin/certifications/stats")
        assert cert_stats_response.status_code == 200
        cert_stats_payload = cert_stats_response.json()
        assert cert_stats_payload["approved"] >= 1

        user_stats_response = await client.get("/api/v1/admin/users/stats")
        assert user_stats_response.status_code == 200
        user_stats = user_stats_response.json()
        assert user_stats["total"] >= 3

        suspend_response = await client.post(
            f"/api/v1/admin/users/{renter_id}/suspend",
            json={"reason": "Chargeback investigation"},
        )
        assert suspend_response.status_code == 200
        assert suspend_response.json()["is_suspended"] is True

    async with context.session_factory() as session:
        updated_kitchen = await session.get(Kitchen, kitchen_id)
        assert updated_kitchen is not None
        assert updated_kitchen.moderation_status is ModerationStatus.APPROVED
        assert updated_kitchen.moderated_at is not None

        updated_cert = await session.get(CertificationDocument, certification_id)
        assert updated_cert is not None
        assert updated_cert.status is CertificationReviewStatus.APPROVED
        assert updated_cert.reviewer_id == context.admin_user.id
        assert updated_cert.verified_at is not None

        suspended_user = await session.get(User, renter_id)
        assert suspended_user is not None
        assert suspended_user.is_suspended is True
        assert suspended_user.suspension_reason == "Chargeback investigation"
        assert isinstance(suspended_user.suspended_at, datetime)
