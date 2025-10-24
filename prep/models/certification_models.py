"""Pydantic models for certification verification workflows."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class VerificationAction(str, Enum):
    """Possible actions an admin can take when reviewing a certification."""

    VERIFY = "verify"
    REJECT = "reject"
    REQUEST_RENEWAL = "request_renewal"


class CertificationDocument(BaseModel):
    """Metadata describing a certification document uploaded by a host."""

    id: UUID
    kitchen_id: UUID
    document_type: str
    file_url: str
    file_name: str
    file_size: int = Field(ge=0)
    uploaded_at: datetime
    uploaded_by: UUID
    status: str
    verified_at: datetime | None = None
    verified_by: UUID | None = None
    rejection_reason: str | None = None
    expiration_date: datetime | None = None
    internal_notes: str | None = None


class PendingCertificationSummary(BaseModel):
    """Lightweight record returned in certification review queues."""

    id: UUID
    kitchen_name: str
    kitchen_id: UUID
    host_name: str
    document_type: str
    uploaded_at: datetime
    days_pending: int = Field(ge=0)
    file_preview_url: str | None = None


class PendingCertificationsResponse(BaseModel):
    """Paginated response envelope for pending certification requests."""

    certifications: list[PendingCertificationSummary] = Field(default_factory=list)
    total_count: int = Field(ge=0)
    has_more: bool


class VerificationEvent(BaseModel):
    """Historical audit entry for certification verification actions."""

    id: UUID
    certification_id: UUID
    admin_id: UUID
    action: VerificationAction
    notes: str | None = None
    created_at: datetime


class CertificationDetail(BaseModel):
    """Full detail presented to admins when verifying certifications."""

    document: CertificationDocument
    kitchen_name: str
    host_name: str
    host_email: str
    history: list[VerificationEvent] = Field(default_factory=list)
    related_certifications: list[CertificationDocument] = Field(default_factory=list)


class CertificationVerificationRequest(BaseModel):
    """Payload submitted by admins when recording a verification decision."""

    action: VerificationAction
    notes: str | None = None
    expiration_date: datetime | None = None
    internal_notes: str | None = None


class VerificationResult(BaseModel):
    """Response returned after processing a verification action."""

    success: bool
    message: str
    certification_id: UUID
    status: str
