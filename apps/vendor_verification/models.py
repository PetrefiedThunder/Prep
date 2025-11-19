"""Pydantic models for the Vendor Verification API."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ============================================================================
# Enums
# ============================================================================


class VendorStatus(str, Enum):
    """Current status of a vendor."""

    ONBOARDING = "onboarding"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRING = "expiring"


class DocumentType(str, Enum):
    """Type of vendor document."""

    BUSINESS_LICENSE = "business_license"
    FOOD_HANDLER_CARD = "food_handler_card"
    LIABILITY_INSURANCE = "liability_insurance"
    OTHER = "other"


class VerificationStatus(str, Enum):
    """Status of a verification run."""

    PENDING_DOCUMENTS = "pending_documents"
    IN_REVIEW = "in_review"
    PASSED = "passed"
    FAILED = "failed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class DecisionOutcome(str, Enum):
    """Overall decision outcome."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


class CheckStatus(str, Enum):
    """Status of an individual check."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


class InitiatedFrom(str, Enum):
    """Source of verification request."""

    API = "api"
    UI = "ui"


# ============================================================================
# Shared Models
# ============================================================================


class Location(BaseModel):
    """Geographic location for jurisdiction."""

    country: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    state: str | None = Field(None, description="State or province code")
    city: str | None = Field(None, description="City name")


class ContactInfo(BaseModel):
    """Contact information."""

    email: EmailStr | None = None
    phone: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(None, description="Optional additional error details")


# ============================================================================
# Vendor Models
# ============================================================================


class VendorRequest(BaseModel):
    """Request to create or update a vendor."""

    external_id: str = Field(..., description="Tenant's own identifier for this vendor")
    legal_name: str = Field(..., description="Legal business name")
    doing_business_as: str | None = Field(None, description="DBA name (optional)")
    contact: ContactInfo | None = None
    tax_id_last4: str | None = Field(
        None, pattern=r"^\d{4}$", description="Last 4 digits of tax ID"
    )
    primary_location: Location


class VendorResponse(BaseModel):
    """Response for vendor resource."""

    model_config = ConfigDict(from_attributes=True)

    vendor_id: UUID
    external_id: str
    legal_name: str
    doing_business_as: str | None = None
    status: VendorStatus
    primary_location: Location
    contact: ContactInfo | None = None
    tax_id_last4: str | None = None
    created_at: datetime
    updated_at: datetime


class VendorListResponse(BaseModel):
    """Response for vendor list."""

    items: list[VendorResponse]
    total: int


# ============================================================================
# Document Models
# ============================================================================


class DocumentRequest(BaseModel):
    """Request to create a vendor document."""

    type: DocumentType
    jurisdiction: Location = Field(..., description="Jurisdiction where this document is valid")
    expires_on: date | None = Field(None, description="Expiration date (optional for now)")
    file_name: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the file")


class DocumentUploadResponse(BaseModel):
    """Response with presigned upload URL."""

    document_id: UUID
    upload_url: str = Field(..., description="Presigned URL for uploading the document")
    upload_expires_in: int = Field(..., description="Seconds until the upload URL expires")


class DocumentResponse(BaseModel):
    """Response for document resource."""

    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    type: DocumentType
    jurisdiction: Location
    expires_on: date | None = None
    file_name: str
    content_type: str
    storage_key: str
    created_at: datetime


class DocumentListResponse(BaseModel):
    """Response for document list."""

    items: list[DocumentResponse]
    total: int


# ============================================================================
# Verification Models
# ============================================================================


class VerificationRequest(BaseModel):
    """Request to create a verification run."""

    kitchen_id: str | None = Field(None, description="Optional kitchen identifier")
    jurisdiction: Location = Field(..., description="Jurisdiction for verification")
    purpose: str = Field(..., description="Purpose of verification")
    requested_by: str | None = Field(
        None, description="Tenant's user ID who requested verification"
    )
    callback_url: str | None = Field(None, description="Optional callback URL")


class VerificationResponse(BaseModel):
    """Response for verification creation."""

    verification_id: UUID
    vendor_id: UUID
    status: VerificationStatus
    jurisdiction: Location
    kitchen_id: str | None = None


class CheckEvidence(BaseModel):
    """Evidence for a check result."""

    document_id: UUID
    note: str | None = None


class CheckResult(BaseModel):
    """Result of an individual check."""

    code: str = Field(..., description="Machine-readable check code")
    status: CheckStatus
    details: str | None = Field(None, description="Human-readable details")
    regulation_version: str | None = Field(None, description="Version of regulation checked")
    evidence: list[CheckEvidence] = Field(default_factory=list)


class Decision(BaseModel):
    """Verification decision."""

    overall: DecisionOutcome
    score: float = Field(..., ge=0, le=1, description="Compliance score (0-1)")
    check_results: list[CheckResult] = Field(default_factory=list)


class Recommendation(BaseModel):
    """Verification recommendation."""

    summary: str = Field(..., description="Summary of recommendation")
    operator_action: str | None = Field(None, description="Recommended action for operator")


class VerificationDetail(BaseModel):
    """Detailed verification information."""

    model_config = ConfigDict(from_attributes=True)

    verification_id: UUID
    vendor_id: UUID
    status: VerificationStatus
    evaluated_at: datetime | None = None
    jurisdiction: Location
    kitchen_id: str | None = None
    decision: Decision
    recommendation: Recommendation
    ruleset_name: str
    regulation_version: str
    engine_version: str
    initiated_by: str | None = None
    initiated_from: InitiatedFrom
    created_at: datetime
    updated_at: datetime
