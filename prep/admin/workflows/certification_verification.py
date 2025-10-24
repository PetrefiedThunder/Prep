"""Business logic supporting certification verification decisions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Dict, Iterable, List, Optional
from uuid import UUID

from prep.models.certification_models import (
    CertificationDocument,
    CertificationDocumentStatus,
    CertificationVerificationRequest,
    VerificationAction,
    VerificationAuditEvent,
    VerificationResult,
)


class CertificationNotFoundError(KeyError):
    """Raised when a certification document cannot be located."""


class CertificationVerificationWorkflow:
    """Encapsulates side-effects required to verify a certification document."""

    def __init__(
        self,
        certifications: Dict[UUID, CertificationDocument],
        *,
        kitchen_statuses: Optional[Dict[UUID, str]] = None,
    ) -> None:
        self._certifications = certifications
        self._kitchen_statuses: Dict[UUID, str] = kitchen_statuses or {}
        self._audit_log: Dict[UUID, List[VerificationAuditEvent]] = {}
        self._notifications: List[dict] = []

    def get_certification(self, cert_id: UUID) -> CertificationDocument:
        """Return the certification document with the provided identifier."""

        try:
            certification = self._certifications[cert_id]
        except KeyError as exc:  # pragma: no cover - defensive
            raise CertificationNotFoundError(cert_id) from exc
        return certification

    async def process_certification_verification(
        self,
        cert_id: UUID,
        admin_id: UUID,
        request: CertificationVerificationRequest,
    ) -> VerificationResult:
        """Process a verification decision and perform required side-effects."""

        certification = self.get_certification(cert_id)
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
        """Mark the certification as verified and persist state."""

        updated = self._apply_updates(
            certification,
            status=CertificationDocumentStatus.VERIFIED,
            verified_at=datetime.now(UTC),
            verified_by=admin_id,
            rejection_reason=None,
            expiration_date=request.expiration_date or certification.expiration_date,
            internal_notes=self._merge_notes(
                certification.internal_notes,
                request.internal_notes or request.notes,
            ),
        )

        return VerificationResult(
            success=True,
            message="Certification verified successfully",
            certification_id=updated.id,
            new_status=updated.status,
        )

    def reject_certification(
        self,
        certification: CertificationDocument,
        admin_id: UUID,
        request: CertificationVerificationRequest,
    ) -> VerificationResult:
        """Reject a certification and capture the rejection rationale."""

        updated = self._apply_updates(
            certification,
            status=CertificationDocumentStatus.REJECTED,
            verified_at=None,
            verified_by=admin_id,
            rejection_reason=request.notes,
            expiration_date=certification.expiration_date,
            internal_notes=self._merge_notes(
                certification.internal_notes,
                request.internal_notes,
            ),
        )

        return VerificationResult(
            success=True,
            message="Certification rejected",
            certification_id=updated.id,
            new_status=updated.status,
        )

    def request_certification_renewal(
        self,
        certification: CertificationDocument,
        admin_id: UUID,
        request: CertificationVerificationRequest,
    ) -> VerificationResult:
        """Set a certification into the renewal requested state."""

        updated = self._apply_updates(
            certification,
            status=CertificationDocumentStatus.RENEWAL_REQUESTED,
            verified_at=None,
            verified_by=admin_id,
            rejection_reason=None,
            expiration_date=request.expiration_date or certification.expiration_date,
            internal_notes=self._merge_notes(
                certification.internal_notes,
                request.internal_notes or request.notes,
            ),
        )

        return VerificationResult(
            success=True,
            message="Renewal requested",
            certification_id=updated.id,
            new_status=updated.status,
        )

    def _apply_updates(
        self,
        certification: CertificationDocument,
        **updates,
    ) -> CertificationDocument:
        """Persist certification updates and refresh kitchen status."""

        updated = certification.model_copy(update=updates)
        self._certifications[updated.id] = updated
        self.update_kitchen_certification_status(updated.kitchen_id)
        return updated

    def update_kitchen_certification_status(self, kitchen_id: UUID) -> str:
        """Recompute the aggregate certification status for a kitchen."""

        docs = self._documents_for_kitchen(kitchen_id)
        status = self._compute_kitchen_status(docs)
        self._kitchen_statuses[kitchen_id] = status
        return status

    def _documents_for_kitchen(self, kitchen_id: UUID) -> List[CertificationDocument]:
        return [
            document
            for document in self._certifications.values()
            if document.kitchen_id == kitchen_id
        ]

    @staticmethod
    def _compute_kitchen_status(documents: Iterable[CertificationDocument]) -> str:
        statuses = {document.status for document in documents}
        if not statuses:
            return "pending"
        if statuses == {CertificationDocumentStatus.VERIFIED}:
            return "verified"
        if CertificationDocumentStatus.EXPIRED in statuses:
            return "expired"
        if CertificationDocumentStatus.RENEWAL_REQUESTED in statuses:
            return "partial"
        if CertificationDocumentStatus.REJECTED in statuses:
            return "partial"
        return "pending"

    def send_verification_notification(
        self, kitchen_id: UUID, status: str, notes: Optional[str] = None
    ) -> None:
        """Simulate dispatching a notification to the host."""

        self._notifications.append(
            {
                "kitchen_id": kitchen_id,
                "status": status,
                "notes": notes,
                "timestamp": datetime.now(UTC),
            }
        )

    def send_renewal_request_notification(
        self, kitchen_id: UUID, notes: Optional[str]
    ) -> None:
        """Simulate notifying the host about a renewal request."""

        self.send_verification_notification(kitchen_id, "renewal_requested", notes)

    def log_verification_event(
        self,
        cert_id: UUID,
        admin_id: UUID,
        action: VerificationAction,
        notes: Optional[str],
    ) -> None:
        """Append an entry to the audit log for the certification."""

        event = VerificationAuditEvent(
            certification_id=cert_id,
            admin_id=admin_id,
            action=action,
            notes=notes,
            occurred_at=datetime.now(UTC),
        )
        self._audit_log.setdefault(cert_id, []).append(event)

    def get_audit_events(self, cert_id: UUID) -> List[VerificationAuditEvent]:
        """Return recorded audit events for a certification."""

        return [
            event.model_copy(deep=True)
            for event in self._audit_log.get(cert_id, [])
        ]

    def get_kitchen_status(self, kitchen_id: UUID) -> Optional[str]:
        """Return the cached certification status for the kitchen."""

        return self._kitchen_statuses.get(kitchen_id)

    def get_notifications(self) -> List[dict]:
        """Expose captured notifications for observability and tests."""

        return list(self._notifications)

    @staticmethod
    def _merge_notes(
        existing: Optional[str],
        additional: Optional[str],
    ) -> Optional[str]:
        if not additional:
            return existing
        if existing:
            return f"{existing}\n{additional}".strip()
        return additional

