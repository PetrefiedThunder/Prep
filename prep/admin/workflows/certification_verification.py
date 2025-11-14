"""In-memory workflow powering certification verification APIs."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from prep.models.pydantic_exports import (
    CertificationDetail,
    CertificationDocument,
    CertificationVerificationRequest,
    PendingCertificationsResponse,
    PendingCertificationSummary,
    VerificationAction,
    VerificationEvent,
    VerificationResult,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, MutableMapping, Sequence


def _sample_certifications() -> tuple[Sequence[CertificationDocument], dict[UUID, dict[str, str]]]:
    """Return deterministic sample certification records for demo purposes."""

    submitted = datetime(2025, 2, 18, 15, 0, tzinfo=UTC)
    kitchens: dict[UUID, dict[str, str]] = {}

    kitchen_one = uuid4()
    kitchens[kitchen_one] = {
        "kitchen_name": "Sunset Loft Kitchen",
        "host_name": "Ava Johnson",
        "host_email": "ava@example.com",
    }
    kitchen_two = uuid4()
    kitchens[kitchen_two] = {
        "kitchen_name": "Harborview Test Kitchen",
        "host_name": "Miguel Santos",
        "host_email": "miguel@example.com",
    }
    kitchen_three = uuid4()
    kitchens[kitchen_three] = {
        "kitchen_name": "Brooklyn Artisan Kitchen",
        "host_name": "Danielle Rivers",
        "host_email": "danielle@example.com",
    }

    documents = [
        CertificationDocument(
            id=uuid4(),
            kitchen_id=kitchen_one,
            document_type="health_department",
            file_url="https://cdn.prepchef.com/certifications/health/sunset-loft.pdf",
            file_name="sunset-loft-health-cert.pdf",
            file_size=245_820,
            uploaded_at=submitted - timedelta(days=3),
            uploaded_by=uuid4(),
            status="pending",
        ),
        CertificationDocument(
            id=uuid4(),
            kitchen_id=kitchen_two,
            document_type="fire_safety",
            file_url="https://cdn.prepchef.com/certifications/fire/harborview.pdf",
            file_name="harborview-fire-safety.pdf",
            file_size=187_334,
            uploaded_at=submitted - timedelta(days=1, hours=6),
            uploaded_by=uuid4(),
            status="pending",
        ),
        CertificationDocument(
            id=uuid4(),
            kitchen_id=kitchen_three,
            document_type="insurance",
            file_url="https://cdn.prepchef.com/certifications/insurance/brooklyn-artisan.pdf",
            file_name="brooklyn-artisan-insurance.pdf",
            file_size=312_110,
            uploaded_at=submitted - timedelta(days=8),
            uploaded_by=uuid4(),
            status="renewal_requested",
            expiration_date=submitted + timedelta(days=30),
        ),
    ]

    return documents, kitchens


class CertificationVerificationWorkflow:
    """Coordinate certification verification flows for the admin dashboard."""

    def __init__(
        self,
        *,
        certifications: Sequence[CertificationDocument] | None = None,
        kitchen_directory: MutableMapping[UUID, dict[str, str]] | None = None,
    ) -> None:
        default_certs, default_directory = _sample_certifications()
        source = certifications or default_certs
        self._certifications: dict[UUID, CertificationDocument] = {
            cert.id: cert.model_copy(deep=True) for cert in source
        }
        self._kitchens: MutableMapping[UUID, dict[str, str]] = (
            kitchen_directory or default_directory
        )
        self._kitchen_statuses: dict[UUID, str] = defaultdict(lambda: "pending")
        self._events: list[VerificationEvent] = []
        self._notifications: list[dict[str, str]] = []

    @property
    def notifications(self) -> Sequence[dict[str, str]]:
        """Expose recorded notification payloads for tests."""
        return tuple(self._notifications)

    async def list_pending_certifications(
        self,
        *,
        kitchen_id: UUID | None = None,
        submitted_after: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PendingCertificationsResponse:
        """Return pending certification documents with filtering and pagination."""

        pending_statuses = {"pending", "renewal_requested"}
        documents = [
            cert for cert in self._certifications.values() if cert.status in pending_statuses
        ]

        if kitchen_id is not None:
            documents = [cert for cert in documents if cert.kitchen_id == kitchen_id]
        if submitted_after is not None:
            documents = [cert for cert in documents if cert.uploaded_at >= submitted_after]

        total_count = len(documents)
        documents.sort(key=lambda cert: cert.uploaded_at, reverse=True)
        window = documents[offset : offset + limit]

        summaries = [self._build_summary(cert) for cert in window]
        has_more = offset + limit < total_count
        return PendingCertificationsResponse(
            certifications=summaries,
            total_count=total_count,
            has_more=has_more,
        )

    def _build_summary(self, certification: CertificationDocument) -> PendingCertificationSummary:
        """Construct a summary object for the moderation queue."""

        metadata = self._kitchens.get(
            certification.kitchen_id,
            {
                "kitchen_name": "Unknown Kitchen",
                "host_name": "Unknown Host",
                "host_email": "unknown@example.com",
            },
        )
        now = datetime.now(tz=UTC)
        days_pending = max(0, int((now - certification.uploaded_at).total_seconds() // 86_400))
        preview_url = f"{certification.file_url}?preview=true"

        return PendingCertificationSummary(
            id=certification.id,
            kitchen_name=metadata["kitchen_name"],
            kitchen_id=certification.kitchen_id,
            host_name=metadata["host_name"],
            document_type=certification.document_type,
            uploaded_at=certification.uploaded_at,
            days_pending=days_pending,
            file_preview_url=preview_url,
        )

    async def get_certification(self, cert_id: UUID) -> CertificationDocument:
        """Retrieve a certification document by its identifier."""

        certification = self._certifications.get(cert_id)
        if certification is None:
            raise LookupError(f"Certification {cert_id} was not found")
        return certification

    async def get_certification_detail(self, cert_id: UUID) -> CertificationDetail:
        """Return certification detail including history and sibling documents."""

        certification = await self.get_certification(cert_id)
        metadata = self._kitchens.get(certification.kitchen_id, {})
        siblings = [
            doc
            for doc in self._certifications.values()
            if doc.kitchen_id == certification.kitchen_id and doc.id != cert_id
        ]
        history = [event for event in self._events if event.certification_id == cert_id]
        history.sort(key=lambda event: event.created_at, reverse=True)

        return CertificationDetail(
            document=certification,
            kitchen_name=metadata.get("kitchen_name", "Unknown Kitchen"),
            host_name=metadata.get("host_name", "Unknown Host"),
            host_email=metadata.get("host_email", "unknown@example.com"),
            history=history,
            related_certifications=siblings,
        )

    async def process_certification_verification(
        self,
        *,
        cert_id: UUID,
        admin_id: UUID,
        request: CertificationVerificationRequest,
    ) -> VerificationResult:
        """Process a verification decision and perform required side-effects."""

        certification = await self.get_certification(cert_id)
        action = request.action

        if action is VerificationAction.VERIFY:
            result = self.verify_certification(certification, admin_id, request)
            self.send_verification_notification(certification.kitchen_id, "approved")
        elif action is VerificationAction.REJECT:
            result = self.reject_certification(certification, admin_id, request)
            self.send_verification_notification(
                certification.kitchen_id,
                "rejected",
                request.notes,
            )
        elif action is VerificationAction.REQUEST_RENEWAL:
            result = self.request_certification_renewal(certification, admin_id, request)
            self.send_renewal_request_notification(
                certification.kitchen_id,
                request.notes,
            )
        else:  # pragma: no cover - exhaustive safety
            raise ValueError(f"Unsupported verification action: {action}")

        self.log_verification_event(cert_id, admin_id, action, request.notes)
        return result

    def verify_certification(
        self,
        certification: CertificationDocument,
        admin_id: UUID,
        request: CertificationVerificationRequest,
    ) -> VerificationResult:
        """Mark the certification as verified."""

        updated = certification.model_copy(
            update={
                "status": "verified",
                "verified_at": datetime.now(tz=UTC),
                "verified_by": admin_id,
                "rejection_reason": None,
                "expiration_date": (
                    request.expiration_date
                    if request.expiration_date is not None
                    else certification.expiration_date
                ),
                "internal_notes": self._merge_notes(
                    certification.internal_notes, request.internal_notes
                ),
            },
        )
        self._certifications[certification.id] = updated
        self.update_kitchen_certification_status(certification.kitchen_id)
        return VerificationResult(
            success=True,
            message="Certification verified successfully",
            certification_id=certification.id,
            status=updated.status,
        )

    def reject_certification(
        self,
        certification: CertificationDocument,
        admin_id: UUID,
        request: CertificationVerificationRequest,
    ) -> VerificationResult:
        """Reject a certification and record the reason."""

        updated = certification.model_copy(
            update={
                "status": "rejected",
                "verified_at": datetime.now(tz=UTC),
                "verified_by": admin_id,
                "rejection_reason": request.notes,
                "internal_notes": self._merge_notes(
                    certification.internal_notes, request.internal_notes
                ),
            },
        )
        self._certifications[certification.id] = updated
        self.update_kitchen_certification_status(certification.kitchen_id)
        return VerificationResult(
            success=True,
            message="Certification rejected",
            certification_id=certification.id,
            status=updated.status,
        )

    def request_certification_renewal(
        self,
        certification: CertificationDocument,
        admin_id: UUID,
        request: CertificationVerificationRequest,
    ) -> VerificationResult:
        """Ask the host to renew or update their certification."""

        updated = certification.model_copy(
            update={
                "status": "renewal_requested",
                "verified_at": datetime.now(tz=UTC),
                "verified_by": admin_id,
                "internal_notes": self._merge_notes(
                    certification.internal_notes, request.internal_notes
                ),
            },
        )
        self._certifications[certification.id] = updated
        self.update_kitchen_certification_status(certification.kitchen_id)
        return VerificationResult(
            success=True,
            message="Renewal requested",
            certification_id=certification.id,
            status=updated.status,
        )

    def update_kitchen_certification_status(self, kitchen_id: UUID) -> None:
        """Recalculate the aggregate certification status for a kitchen."""

        statuses = {
            cert.status for cert in self._certifications.values() if cert.kitchen_id == kitchen_id
        }
        if not statuses:
            aggregate = "pending"
        elif statuses == {"verified"}:
            aggregate = "verified"
        elif "pending" in statuses or "renewal_requested" in statuses:
            aggregate = "pending"
        elif "expired" in statuses:
            aggregate = "expired"
        else:
            aggregate = "partial"

        self._kitchen_statuses[kitchen_id] = aggregate

    def send_verification_notification(
        self,
        kitchen_id: UUID,
        outcome: str,
        notes: str | None = None,
    ) -> None:
        """Record that a notification would be sent to the host."""

        metadata = self._kitchens.get(kitchen_id, {})
        self._notifications.append(
            {
                "kitchen_id": str(kitchen_id),
                "kitchen_name": metadata.get("kitchen_name", "Unknown Kitchen"),
                "outcome": outcome,
                "notes": notes or "",
            },
        )

    def send_renewal_request_notification(
        self,
        kitchen_id: UUID,
        notes: str | None = None,
    ) -> None:
        """Alias for sending renewal specific notifications."""

        self.send_verification_notification(kitchen_id, "renewal_requested", notes)

    def log_verification_event(
        self,
        cert_id: UUID,
        admin_id: UUID,
        action: VerificationAction,
        notes: str | None,
    ) -> None:
        """Persist a verification event in the in-memory audit trail."""

        event = VerificationEvent(
            id=uuid4(),
            certification_id=cert_id,
            admin_id=admin_id,
            action=action,
            notes=notes,
            created_at=datetime.now(tz=UTC),
        )
        self._events.append(event)

    def _merge_notes(self, existing: str | None, new_notes: str | None) -> str | None:
        """Combine note fields without losing previous context."""

        if not existing:
            return new_notes
        if not new_notes:
            return existing
        return f"{existing}\n---\n{new_notes}"

    def get_kitchen_status(self, kitchen_id: UUID) -> str:
        """Expose aggregate certification status for testing."""

        return self._kitchen_statuses[kitchen_id]

    def iter_certifications(self) -> Iterable[CertificationDocument]:
        """Yield certification documents (primarily for tests)."""

        return tuple(self._certifications.values())
