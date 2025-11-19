from __future__ import annotations

import importlib.util
import os
import sys
import types
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from prep.admin.api import router as admin_router
from prep.admin.dependencies import get_current_admin as admin_get_current_admin
from prep.analytics.dashboard_api import get_dashboard_service, router as analytics_router
from prep.auth import require_admin_role as auth_get_current_admin
from prep.database import get_db as core_get_db
from prep.database.connection import get_db as connection_get_db
from prep.models.admin import AdminUser
from prep.models.orm import (
    Base,
    Booking,
    CertificationDocument,
    CertificationReviewStatus,
    Kitchen,
    ModerationStatus,
    User,
    UserRole,
)
from tests.integration.test_analytics_dashboard_api import StubAnalyticsDashboardService

_BOOKINGS_SPEC = importlib.util.spec_from_file_location(
    "tests.e2e.bookings", Path(__file__).resolve().parents[2] / "prep" / "api" / "bookings.py"
)
assert _BOOKINGS_SPEC and _BOOKINGS_SPEC.loader  # nosec - runtime assertion for test harness
_bookings_module = importlib.util.module_from_spec(_BOOKINGS_SPEC)
# Provide stub module to satisfy relative imports inside bookings.py
_stub_kitchens = types.ModuleType("tests.e2e.kitchens")
_stub_kitchens.analyze_kitchen_compliance = lambda kitchen_id: None
sys.modules.setdefault("tests.e2e.kitchens", _stub_kitchens)
_BOOKINGS_SPEC.loader.exec_module(_bookings_module)
if hasattr(_bookings_module, "BookingCreate"):
    _bookings_module.BookingCreate.model_rebuild()
if hasattr(_bookings_module, "BookingResponse"):
    _bookings_module.BookingResponse.model_rebuild()
bookings_router = _bookings_module.router

pytestmark = pytest.mark.anyio("asyncio")


@dataclass
class FullAppContext:
    app: FastAPI
    session_factory: async_sessionmaker[AsyncSession]
    admin_user: AdminUser
    admin_record_id: UUID


@pytest.fixture
async def full_app_context() -> FullAppContext:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(bookings_router)
    app.include_router(admin_router)
    app.include_router(analytics_router)
    admin_id = uuid4()
    admin_profile = AdminUser(
        id=admin_id,
        email="ops-admin@example.com",
        full_name="Ops Admin",
        permissions=["moderate", "analytics"],
    )

    async def _get_db() -> AsyncSession:
        async with session_factory() as session:
            yield session

    async def _get_admin_profile() -> AdminUser:
        return admin_profile

    app.dependency_overrides[core_get_db] = _get_db
    app.dependency_overrides[connection_get_db] = _get_db
    app.dependency_overrides[admin_get_current_admin] = _get_admin_profile

    async with session_factory() as session:
        admin_record = User(
            id=admin_id,
            email=admin_profile.email,
            full_name=admin_profile.full_name,
            role=UserRole.ADMIN,
            is_active=True,
            is_admin=True,
        )
        session.add(admin_record)
        await session.commit()
        await session.refresh(admin_record)

    async def _get_auth_admin() -> User:
        return admin_record

    app.dependency_overrides[auth_get_current_admin] = _get_auth_admin

    yield FullAppContext(
        app=app,
        session_factory=session_factory,
        admin_user=admin_profile,
        admin_record_id=admin_record.id,
    )

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.anyio
async def test_full_platform_flow(
    full_app_context: FullAppContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = full_app_context

    async with context.session_factory() as session:
        host = User(
            email="flow-host@example.com",
            full_name="Flow Host",
            role=UserRole.HOST,
            is_active=True,
        )
        customer = User(
            email="flow-customer@example.com",
            full_name="Flow Customer",
            role=UserRole.CUSTOMER,
            is_active=True,
        )
        kitchen = Kitchen(
            host=host,
            name="Flow Kitchen",
            description="Kitchen for full e2e flow",
            address="456 Market St",
            location="Austin",
            city="Austin",
            state="TX",
            hourly_rate=Decimal("95.00"),
            trust_score=4.6,
            moderation_status=ModerationStatus.PENDING,
            certification_status=CertificationReviewStatus.PENDING,
            compliance_status="compliant",
        )
        certification = CertificationDocument(
            kitchen=kitchen,
            document_type="fire_certificate",
            document_url="https://example.com/fire.pdf",
            status=CertificationReviewStatus.PENDING,
        )
        session.add_all([host, customer, kitchen, certification])
        await session.commit()
        await session.refresh(kitchen)
        await session.refresh(customer)
        await session.refresh(certification)
        certification_id = certification.id

    start_time = datetime.now(UTC) + timedelta(days=1)
    end_time = start_time + timedelta(hours=4)

    transport = ASGITransport(app=context.app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        booking_response = await client.post(
            "/bookings/",
            json={
                "user_id": str(customer.id),
                "kitchen_id": str(kitchen.id),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )
        assert booking_response.status_code == 201
        booking_payload = booking_response.json()
        assert booking_payload["status"] == "pending"
        booking_id = booking_payload["id"]

        moderation_response = await client.post(
            f"/api/v1/admin/kitchens/{kitchen.id}/moderate",
            json={"action": "approve"},
        )
        assert moderation_response.status_code == 200
        assert moderation_response.json()["kitchen"]["moderation_status"] == "approved"

        cert_response = await client.post(
            f"/api/v1/admin/certifications/{certification_id}/verify",
            json={"approve": True},
        )
        assert cert_response.status_code == 200
        assert cert_response.json()["certification"]["status"] == "approved"

        stub_service = StubAnalyticsDashboardService()

        async def _get_service():
            return stub_service

        context.app.dependency_overrides[get_dashboard_service] = _get_service
        analytics_response = await client.get("/api/v1/analytics/admin/financial")
        assert analytics_response.status_code == 200
        assert analytics_response.json()["net_revenue"] == "88000.00"

    context.app.dependency_overrides.pop(get_dashboard_service, None)

    async with context.session_factory() as session:
        stored_booking = await session.get(Booking, UUID(booking_id))
        assert stored_booking is not None
        assert stored_booking.kitchen_id == kitchen.id
        assert stored_booking.customer_id == customer.id

        updated_cert = await session.get(CertificationDocument, certification_id)
        assert updated_cert is not None
        assert updated_cert.status is CertificationReviewStatus.APPROVED
