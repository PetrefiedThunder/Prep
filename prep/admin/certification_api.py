"""FastAPI router powering certification verification endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from prep.admin.workflows import CertificationVerificationWorkflow
from prep.models import (
    AdminUser,
    CertificationDetail,
    CertificationVerificationRequest,
    PendingCertificationsResponse,
    VerificationResult,
)

if TYPE_CHECKING:
    from datetime import datetime

router = APIRouter()

_WORKFLOW = CertificationVerificationWorkflow()


async def get_current_admin() -> AdminUser:
    """Stub dependency returning the authenticated admin user."""

    return AdminUser(
        id=uuid4(),
        email="admin@example.com",
        full_name="Prep Admin",
        permissions=["certifications:verify"],
    )


@router.get("/api/v1/admin/certifications/pending", response_model=PendingCertificationsResponse)
async def get_pending_certifications(
    current_admin: AdminUser = Depends(get_current_admin),
    kitchen_id: UUID | None = Query(default=None, description="Filter by kitchen identifier"),
    submitted_after: datetime | None = Query(
        default=None, description="Return certifications submitted on or after this timestamp",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PendingCertificationsResponse:
    """Get pending certification documents for review."""

    _ = current_admin  # dependency ensures authentication in real deployment
    return await _WORKFLOW.list_pending_certifications(
        kitchen_id=kitchen_id,
        submitted_after=submitted_after,
        limit=limit,
        offset=offset,
    )


@router.get("/api/v1/admin/certifications/{cert_id}", response_model=CertificationDetail)
async def get_certification_detail(
    cert_id: UUID,
    current_admin: AdminUser = Depends(get_current_admin),
) -> CertificationDetail:
    """Retrieve detailed certification information for verification."""

    _ = current_admin
    try:
        return await _WORKFLOW.get_certification_detail(cert_id)
    except LookupError as exc:  # pragma: no cover - protective guard
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/api/v1/admin/certifications/{cert_id}/verify",
    response_model=VerificationResult,
)
async def verify_certification(
    cert_id: UUID,
    verification_request: CertificationVerificationRequest,
    current_admin: AdminUser = Depends(get_current_admin),
) -> VerificationResult:
    """Verify or reject a certification document."""

    try:
        return await _WORKFLOW.process_certification_verification(
            cert_id=cert_id,
            admin_id=current_admin.id,
            request=verification_request,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
