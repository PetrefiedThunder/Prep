"""FastAPI router exposing certification verification endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Dict, Iterable, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from prep.admin.workflows import CertificationVerificationWorkflow
from prep.admin.workflows.certification_verification import CertificationNotFoundError
from prep.models.admin import AdminUser
from prep.models.certification_models import (
    CertificationDetail,
    CertificationDocument,
    CertificationDocumentStatus,
    CertificationVerificationRequest,
    PendingCertificationsResponse,
    PendingCertificationSummary,
    VerificationAction,
    VerificationResult,
)

certification_router = APIRouter(prefix="/api/v1/admin/certifications", tags=["admin", "certifications"])


class KitchenContext(BaseModel):
    """Lightweight context describing a kitchen and its host."""

    id: UUID
    name: str
    host_id: UUID
    host_name: str
    host_email: str
    certification_status: str = Field(default="pending")


SUNSET_KITCHEN_ID = UUID("11111111-1111-1111-1111-111111111111")
HARBORVIEW_KITCHEN_ID = UUID("22222222-2222-2222-2222-222222222222")
BROOKLYN_KITCHEN_ID = UUID("33333333-3333-3333-3333-333333333333")

SUNSET_HEALTH_CERT_ID = UUID("aaaa1111-0000-0000-0000-000000000001")
HARBORVIEW_FIRE_CERT_ID = UUID("aaaa1111-0000-0000-0000-000000000002")
BROOKLYN_INSURANCE_CERT_ID = UUID("aaaa1111-0000-0000-0000-000000000003")


class CertificationVerificationAPI:
    """Application service backing certification moderation workflows."""

    def __init__(
        self,
        *,
        certifications: Optional[Dict[UUID, CertificationDocument]] = None,
        workflow: Optional[CertificationVerificationWorkflow] = None,
    ) -> None:
        self._kitchens: Dict[UUID, KitchenContext] = self._seed_kitchens()
        self._certifications: Dict[UUID, CertificationDocument] = certifications or {
            doc.id: doc for doc in self._seed_certifications()
        }
        self._workflow = workflow or CertificationVerificationWorkflow(
            self._certifications,
            kitchen_statuses={kitchen_id: ctx.certification_status for kitchen_id, ctx in self._kitchens.items()},
        )
        self._refresh_all_kitchen_statuses()

    def get_pending_certifications(
        self,
        *,
        kitchen_id: Optional[UUID] = None,
        submitted_after: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PendingCertificationsResponse:
        """Return a paginated list of certifications awaiting verification."""

        pending_statuses = {
            CertificationDocumentStatus.PENDING,
            CertificationDocumentStatus.RENEWAL_REQUESTED,
        }
        documents: List[CertificationDocument] = [
            document.model_copy(deep=True)
            for document in self._certifications.values()
            if document.status in pending_statuses
        ]

        if kitchen_id:
            documents = [doc for doc in documents if doc.kitchen_id == kitchen_id]
        if submitted_after:
            documents = [
                doc
                for doc in documents
                if doc.uploaded_at >= submitted_after
            ]

        documents.sort(key=lambda doc: doc.uploaded_at, reverse=True)

        total_count = len(documents)
        page = documents[offset : offset + limit]
        now = datetime.now(UTC)
        summaries = [
            self._to_pending_summary(document, now)
            for document in page
        ]

        return PendingCertificationsResponse(
            certifications=summaries,
            total_count=total_count,
            has_more=offset + len(page) < total_count,
        )

    def get_certification_detail(self, cert_id: UUID) -> CertificationDetail:
        """Return the full certification record for review."""

        try:
            document = self._certifications[cert_id]
        except KeyError as exc:
            raise CertificationNotFoundError(cert_id) from exc

        context = self._kitchens.get(document.kitchen_id)
        if context is None:  # pragma: no cover - defensive safety
            raise RuntimeError("Kitchen context unavailable")

        return CertificationDetail(
            certification=document.model_copy(deep=True),
            kitchen_id=context.id,
            kitchen_name=context.name,
            host_id=context.host_id,
            host_name=context.host_name,
            host_email=context.host_email,
            status_history=self._workflow.get_audit_events(cert_id),
            available_actions=self._available_actions(document.status),
        )

    async def verify_certification(
        self,
        cert_id: UUID,
        request: CertificationVerificationRequest,
        admin: AdminUser,
    ) -> VerificationResult:
        """Process a verification decision issued by an administrator."""

        try:
            result = await self._workflow.process_certification_verification(
                cert_id,
                admin.id,
                request,
            )
        except CertificationNotFoundError:
            raise

        self._sync_kitchen_status_for_cert(cert_id)
        return result

    def _sync_kitchen_status_for_cert(self, cert_id: UUID) -> None:
        document = self._certifications.get(cert_id)
        if not document:
            return
        status = self._workflow.get_kitchen_status(document.kitchen_id)
        context = self._kitchens.get(document.kitchen_id)
        if status and context:
            context.certification_status = status

    def _to_pending_summary(
        self, document: CertificationDocument, now: datetime
    ) -> PendingCertificationSummary:
        context = self._kitchens.get(document.kitchen_id)
        if context is None:  # pragma: no cover - defensive safety
            raise RuntimeError("Kitchen context unavailable")

        elapsed = now - document.uploaded_at
        days_pending = max(0, int(elapsed.total_seconds() // 86400))

        return PendingCertificationSummary(
            id=document.id,
            kitchen_name=context.name,
            kitchen_id=document.kitchen_id,
            host_name=context.host_name,
            document_type=document.document_type,
            uploaded_at=document.uploaded_at,
            days_pending=days_pending,
            file_preview_url=document.file_url,
        )

    def _refresh_all_kitchen_statuses(self) -> None:
        for kitchen_id in self._kitchens:
            status = self._workflow.update_kitchen_certification_status(kitchen_id)
            self._kitchens[kitchen_id].certification_status = status

    def _available_actions(
        self, status: CertificationDocumentStatus
    ) -> List[VerificationAction]:
        if status is CertificationDocumentStatus.PENDING:
            return [
                VerificationAction.VERIFY,
                VerificationAction.REJECT,
                VerificationAction.REQUEST_RENEWAL,
            ]
        if status is CertificationDocumentStatus.RENEWAL_REQUESTED:
            return [VerificationAction.VERIFY, VerificationAction.REJECT]
        if status is CertificationDocumentStatus.VERIFIED:
            return [VerificationAction.REQUEST_RENEWAL]
        if status is CertificationDocumentStatus.REJECTED:
            return [VerificationAction.VERIFY]
        if status is CertificationDocumentStatus.EXPIRED:
            return [VerificationAction.VERIFY, VerificationAction.REQUEST_RENEWAL]
        return [VerificationAction.VERIFY]

    @staticmethod
    def _seed_kitchens() -> Dict[UUID, KitchenContext]:
        """Return deterministic kitchens for use in local development."""

        return {
            SUNSET_KITCHEN_ID: KitchenContext(
                id=SUNSET_KITCHEN_ID,
                name="Sunset Loft Kitchen",
                host_id=UUID("88888888-8888-8888-8888-888888888881"),
                host_name="Ava Johnson",
                host_email="ava@example.com",
            ),
            HARBORVIEW_KITCHEN_ID: KitchenContext(
                id=HARBORVIEW_KITCHEN_ID,
                name="Harborview Test Kitchen",
                host_id=UUID("88888888-8888-8888-8888-888888888882"),
                host_name="Miguel Santos",
                host_email="miguel@example.com",
            ),
            BROOKLYN_KITCHEN_ID: KitchenContext(
                id=BROOKLYN_KITCHEN_ID,
                name="Brooklyn Artisan Kitchen",
                host_id=UUID("88888888-8888-8888-8888-888888888883"),
                host_name="Danielle Rivers",
                host_email="danielle@example.com",
            ),
        }

    @staticmethod
    def _seed_certifications() -> Iterable[CertificationDocument]:
        """Return a deterministic set of sample certification documents."""

        uploaded_base = datetime(2025, 1, 15, 15, 30, tzinfo=UTC)
        return [
            CertificationDocument(
                id=SUNSET_HEALTH_CERT_ID,
                kitchen_id=SUNSET_KITCHEN_ID,
                document_type="health_department",
                file_url="https://cdn.prepchef.com/certs/sunset-health.pdf",
                file_name="sunset_health.pdf",
                file_size=524288,
                uploaded_at=uploaded_base,
                uploaded_by=UUID("99999999-9999-9999-9999-999999999991"),
            ),
            CertificationDocument(
                id=HARBORVIEW_FIRE_CERT_ID,
                kitchen_id=HARBORVIEW_KITCHEN_ID,
                document_type="fire_safety",
                file_url="https://cdn.prepchef.com/certs/harborview-fire.pdf",
                file_name="harborview_fire.pdf",
                file_size=786432,
                uploaded_at=uploaded_base.replace(day=10),
                uploaded_by=UUID("99999999-9999-9999-9999-999999999992"),
                status=CertificationDocumentStatus.RENEWAL_REQUESTED,
                expiration_date=uploaded_base.replace(year=2025, month=6, day=10),
            ),
            CertificationDocument(
                id=BROOKLYN_INSURANCE_CERT_ID,
                kitchen_id=BROOKLYN_KITCHEN_ID,
                document_type="insurance",
                file_url="https://cdn.prepchef.com/certs/brooklyn-insurance.pdf",
                file_name="brooklyn_insurance.pdf",
                file_size=655360,
                uploaded_at=uploaded_base.replace(day=2),
                uploaded_by=UUID("99999999-9999-9999-9999-999999999993"),
                status=CertificationDocumentStatus.VERIFIED,
                verified_at=uploaded_base.replace(day=16),
                verified_by=UUID("77777777-7777-7777-7777-777777777777"),
            ),
        ]


_certification_api: Optional[CertificationVerificationAPI] = None


def get_certification_verification_api() -> CertificationVerificationAPI:
    """Return a lazily instantiated certification verification API."""

    global _certification_api
    if _certification_api is None:
        _certification_api = CertificationVerificationAPI()
    return _certification_api


async def get_current_admin() -> AdminUser:
    """Dependency stub returning the current authenticated admin user."""

    return AdminUser(
        id=UUID("55555555-5555-5555-5555-555555555555"),
        email="admin@example.com",
        name="Prep Admin",
    )


@certification_router.get("/pending", response_model=PendingCertificationsResponse)
async def list_pending_certifications(
    *,
    current_admin: AdminUser = Depends(get_current_admin),
    kitchen_id: Optional[UUID] = None,
    submitted_after: Optional[datetime] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    api: CertificationVerificationAPI = Depends(get_certification_verification_api),
) -> PendingCertificationsResponse:
    """Fetch pending certification documents for moderator review."""

    # current_admin dependency retained for parity with protected endpoints
    _ = current_admin
    return api.get_pending_certifications(
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


@certification_router.get("/{cert_id}", response_model=CertificationDetail)
async def get_certification_detail_endpoint(
    cert_id: UUID,
    current_admin: AdminUser = Depends(get_current_admin),
    api: CertificationVerificationAPI = Depends(get_certification_verification_api),
) -> CertificationDetail:
    """Fetch the full certification document details for review."""

    _ = current_admin
    try:
        return api.get_certification_detail(cert_id)
    except CertificationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Certification not found") from exc


@certification_router.post("/{cert_id}/verify", response_model=VerificationResult)
async def verify_certification_endpoint(
    cert_id: UUID,
    verification_request: CertificationVerificationRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    api: CertificationVerificationAPI = Depends(get_certification_verification_api),
) -> VerificationResult:
    """Verify, reject, or request renewal for a certification document."""

    try:
        return await api.verify_certification(cert_id, verification_request, current_admin)
    except CertificationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Certification not found") from exc


__all__ = [
    "CertificationVerificationAPI",
    "get_certification_verification_api",
    "certification_router",
]

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
