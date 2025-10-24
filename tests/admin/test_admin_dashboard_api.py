from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from prep.admin import AdminDashboardAPI, get_admin_dashboard_api, router
from prep.models.admin import (
    CertificationStatus,
    ModerationAction,
    ModerationFilters,
    Pagination,
    PendingKitchen,
    PlatformOverview,
    SortField,
    SortOrder,
)


def _kitchen(
    *,
    kitchen_id: str,
    host_id: str,
    name: str,
    trust_score: float,
    submitted_at: datetime,
    certification_status: CertificationStatus,
    certification_type: str,
    status: str = "pending_review",
    hourly_rate: str = "100.00",
) -> PendingKitchen:
    return PendingKitchen(
        id=UUID(kitchen_id),
        name=name,
        host_id=UUID(host_id),
        host_name=f"Host {name}",
        host_email=f"{name.lower().replace(' ', '_')}@example.com",
        location="Test City",
        submitted_at=submitted_at,
        photos=[],
        certification_status=certification_status,
        certification_type=certification_type,
        trust_score=trust_score,
        equipment_count=10,
        hourly_rate=Decimal(hourly_rate),
        status=status,
    )


def test_get_pending_kitchens_applies_filters_and_pagination() -> None:
    submitted = datetime(2025, 1, 10, tzinfo=timezone.utc)
    kitchens = [
        _kitchen(
            kitchen_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            host_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            name="Alpha Kitchen",
            trust_score=4.8,
            submitted_at=submitted,
            certification_status=CertificationStatus.PENDING_REVIEW,
            certification_type="health_department",
        ),
        _kitchen(
            kitchen_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
            host_id="dddddddd-dddd-dddd-dddd-dddddddddddd",
            name="Beta Kitchen",
            trust_score=3.5,
            submitted_at=submitted.replace(day=9),
            certification_status=CertificationStatus.PENDING_UPLOAD,
            certification_type="food_handler",
        ),
        _kitchen(
            kitchen_id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            host_id="ffffffff-ffff-ffff-ffff-ffffffffffff",
            name="Gamma Kitchen",
            trust_score=4.4,
            submitted_at=submitted.replace(day=8),
            certification_status=CertificationStatus.PENDING_REVIEW,
            certification_type="health_department",
        ),
    ]

    api = AdminDashboardAPI(pending_kitchens=kitchens)
    filters = ModerationFilters(
        certification_status=CertificationStatus.PENDING_REVIEW,
        min_trust_score=4.0,
    )
    pagination = Pagination(limit=1, offset=0, sort_by=SortField.TRUST_SCORE, sort_order=SortOrder.DESC)

    response = api.get_pending_kitchens(filters, pagination)

    assert response.total_count == 2
    assert len(response.kitchens) == 1
    assert response.kitchens[0].name == "Alpha Kitchen"
    assert response.has_more is True


def test_moderate_kitchen_updates_status_and_queue() -> None:
    submitted = datetime(2025, 1, 10, tzinfo=timezone.utc)
    kitchen = _kitchen(
        kitchen_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        host_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        name="Alpha Kitchen",
        trust_score=4.8,
        submitted_at=submitted,
        certification_status=CertificationStatus.PENDING_REVIEW,
        certification_type="health_department",
    )
    api = AdminDashboardAPI(pending_kitchens=[kitchen])

    result = api.moderate_kitchen(kitchen_id=kitchen.id, action=ModerationAction.APPROVE, reason="Meets standards")

    assert result.new_status is CertificationStatus.VERIFIED
    assert len(api.pending_kitchens) == 0


def test_platform_overview_counts_verified_kitchens() -> None:
    submitted = datetime(2025, 1, 10, tzinfo=timezone.utc)
    kitchen = _kitchen(
        kitchen_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        host_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        name="Alpha Kitchen",
        trust_score=4.8,
        submitted_at=submitted,
        certification_status=CertificationStatus.PENDING_REVIEW,
        certification_type="health_department",
    )
    overview_seed = PlatformOverview(
        total_kitchens=1,
        active_kitchens=0,
        total_bookings=10,
        revenue_this_month=Decimal("1500.00"),
        conversion_rate=0.25,
        user_satisfaction=4.5,
        new_users_this_week=5,
    )
    api = AdminDashboardAPI(pending_kitchens=[kitchen], overview_seed=overview_seed)
    api.moderate_kitchen(kitchen_id=kitchen.id, action=ModerationAction.APPROVE)

    overview = api.get_platform_overview()

    assert overview.total_kitchens == 1
    assert overview.active_kitchens == 1
    assert overview.revenue_this_month == Decimal("1500.00")


def test_fastapi_router_endpoints() -> None:
    submitted = datetime(2025, 1, 10, tzinfo=timezone.utc)
    kitchens = [
        _kitchen(
            kitchen_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            host_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            name="Alpha Kitchen",
            trust_score=4.8,
            submitted_at=submitted,
            certification_status=CertificationStatus.PENDING_REVIEW,
            certification_type="health_department",
        ),
        _kitchen(
            kitchen_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
            host_id="dddddddd-dddd-dddd-dddd-dddddddddddd",
            name="Beta Kitchen",
            trust_score=3.9,
            submitted_at=submitted.replace(day=9),
            certification_status=CertificationStatus.PENDING_UPLOAD,
            certification_type="food_handler",
        ),
    ]
    overview_seed = PlatformOverview(
        total_kitchens=2,
        active_kitchens=0,
        total_bookings=20,
        revenue_this_month=Decimal("3200.00"),
        conversion_rate=0.2,
        user_satisfaction=4.4,
        new_users_this_week=7,
    )
    api = AdminDashboardAPI(pending_kitchens=kitchens, overview_seed=overview_seed)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_admin_dashboard_api] = lambda: api

    client = TestClient(app)

    list_response = client.get(
        "/api/v1/admin/kitchens/pending",
        params={"certification_status": CertificationStatus.PENDING_REVIEW.value},
    )
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total_count"] == 1
    assert payload["kitchens"][0]["name"] == "Alpha Kitchen"

    moderate_response = client.post(
        "/api/v1/admin/kitchens/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/moderate",
        json={"action": ModerationAction.APPROVE.value, "reason": "Looks good"},
    )
    assert moderate_response.status_code == 200
    assert moderate_response.json()["new_status"] == CertificationStatus.VERIFIED.value

    overview_response = client.get("/api/v1/admin/analytics/overview")
    assert overview_response.status_code == 200
    overview_payload = overview_response.json()
    assert overview_payload["total_kitchens"] == 2
    assert overview_payload["active_kitchens"] == 1
    assert overview_payload["revenue_this_month"] == "3200.00"
