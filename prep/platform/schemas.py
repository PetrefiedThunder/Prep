"""Pydantic schemas powering the core platform API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Any, Sequence
from uuid import UUID

from pydantic import AnyUrl, BaseModel, ConfigDict, EmailStr, Field, field_validator

from prep.models.orm import (
    APIKey,
    Booking,
    BookingStatus,
    BusinessPermit,
    ComplianceDocument,
    ComplianceDocumentStatus,
    DocumentProcessingStatus,
    DocumentUpload,
    Kitchen,
    PaymentStatus,
    BusinessProfile,
    CheckoutPayment,
    CheckoutPaymentStatus,
    ComplianceDocument,
    ComplianceDocumentStatus,
    DocumentOCRStatus,
    DocumentUpload,
    DocumentUploadStatus,
    Kitchen,
    Permit,
    PermitStatus,
    Review,
    SubleaseContractStatus,
    User,
    UserRole,
)


class ErrorDetail(BaseModel):
    """Machine-readable description of a request failure."""

    code: str = Field(description="Stable identifier for the error condition")
    message: str = Field(description="Human readable explanation of the error")
    target: str | None = Field(
        default=None,
        description="Optional field or domain that triggered the error",
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional structured context for debugging"
    )


class ErrorResponse(BaseModel):
    """Canonical error envelope returned by Prep APIs."""

    request_id: str = Field(description="Server assigned identifier for this request")
    error: ErrorDetail


class CursorPageMeta(BaseModel):
    """Pagination metadata used by cursor-based collection endpoints."""

    cursor: str | None = Field(
        default=None,
        description="Cursor supplied in the request that produced this page",
    )
    next_cursor: str | None = Field(
        default=None,
        description="Cursor to request the next page, if additional records exist",
    )
    limit: int = Field(default=20, ge=1, le=100, description="Maximum page size")
    has_more: bool = Field(description="Whether more results are available")


class _ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserRegistrationRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.CUSTOMER


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(_ORMBaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    rbac_roles: list[str] = Field(default_factory=list)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    refresh_token: str | None = None


class TokenPairResponse(AuthTokenResponse):
    refresh_token: str
    refresh_expires_at: datetime


class AuthenticatedUserResponse(TokenPairResponse):
    user: UserResponse


class TokenPairResponse(AuthTokenResponse):
    refresh_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=16)
class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)
    device_fingerprint: str | None = Field(default=None, max_length=255)
    ip_address: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=255)


class APIKeyIssueRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class APIKeyRotateRequest(BaseModel):
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class APIKeyResponse(_ORMBaseModel):
    id: UUID
    name: str
    prefix: str
    is_active: bool
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    rotated_at: datetime | None
    revoked_at: datetime | None


class APIKeyIssueResponse(APIKeyResponse):
    secret: str


def serialize_api_key(api_key: APIKey) -> APIKeyResponse:
    return APIKeyResponse.model_validate(api_key)


def serialize_api_key_issue(api_key: APIKey, secret: str) -> APIKeyIssueResponse:
    payload = serialize_api_key(api_key).model_dump()
    payload["secret"] = secret
    return APIKeyIssueResponse(**payload)


class KitchenCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    host_id: UUID
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=60)
    hourly_rate: float = Field(ge=0)
    trust_score: float | None = Field(default=None, ge=0, le=5)
    moderation_status: str | None = None
    certification_status: str | None = None
    published: bool = False


class KitchenUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=60)
    hourly_rate: float | None = Field(default=None, ge=0)
    trust_score: float | None = Field(default=None, ge=0, le=5)
    moderation_status: str | None = None
    certification_status: str | None = None
    published: bool | None = None


class KitchenResponse(_ORMBaseModel):
    id: UUID
    name: str
    description: str | None
    host_id: UUID
    city: str | None
    state: str | None
    hourly_rate: float
    trust_score: float | None
    moderation_status: str
    certification_status: str
    published: bool
    created_at: datetime


class BookingCreateRequest(BaseModel):
    host_id: UUID
    customer_id: UUID
    kitchen_id: UUID
    start_time: datetime
    end_time: datetime
    status: BookingStatus = BookingStatus.PENDING
    total_amount: float = Field(ge=0)
    platform_fee: float = Field(default=0, ge=0)
    host_payout_amount: float = Field(default=0, ge=0)
    payment_method: str = Field(default="card", max_length=50)
    source: str | None = Field(default=None, max_length=120)


class BookingStatusUpdateRequest(BaseModel):
    status: BookingStatus
    cancellation_reason: str | None = Field(default=None, max_length=120)


class BookingResponse(_ORMBaseModel):
    id: UUID
    host_id: UUID
    customer_id: UUID
    kitchen_id: UUID
    status: BookingStatus
    start_time: datetime
    end_time: datetime
    total_amount: float
    platform_fee: float
    host_payout_amount: float
    payment_method: str
    source: str | None
    cancellation_reason: str | None
    created_at: datetime


class ReviewCreateRequest(BaseModel):
    booking_id: UUID
    kitchen_id: UUID
    host_id: UUID
    customer_id: UUID
    rating: float = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
    equipment_rating: float | None = Field(default=None, ge=0, le=5)
    cleanliness_rating: float | None = Field(default=None, ge=0, le=5)
    communication_rating: float | None = Field(default=None, ge=0, le=5)
    value_rating: float | None = Field(default=None, ge=0, le=5)


class ReviewResponse(_ORMBaseModel):
    id: UUID
    booking_id: UUID
    kitchen_id: UUID
    host_id: UUID
    customer_id: UUID
    rating: float
    comment: str | None
    created_at: datetime


class ReviewListResponse(BaseModel):
    """Cursor paginated list of kitchen reviews."""

    items: list[ReviewResponse]
    pagination: CursorPageMeta


class ComplianceDocumentCreateRequest(BaseModel):
    kitchen_id: UUID
    uploader_id: UUID | None = None
    document_type: str = Field(min_length=1, max_length=120)
    document_url: str = Field(min_length=1, max_length=512)
    verification_status: ComplianceDocumentStatus = ComplianceDocumentStatus.PENDING
    notes: str | None = Field(default=None, max_length=2000)


class ComplianceDocumentResponse(_ORMBaseModel):
    id: UUID
    kitchen_id: UUID
    uploader_id: UUID | None
    reviewer_id: UUID | None
    document_type: str
    document_url: str
    verification_status: ComplianceDocumentStatus
    submitted_at: datetime
    reviewed_at: datetime | None
    notes: str | None


class DocumentUploadRequest(BaseModel):
    business_id: UUID
    uploader_id: UUID | None = None
    permit_id: UUID | None = None
    file_name: str = Field(min_length=1, max_length=255)
    file_url: AnyUrl
    content_type: str | None = Field(default=None, max_length=120)
    storage_bucket: str | None = Field(default=None, max_length=255)
    trigger_ocr: bool = True
    requirement_key: str | None = Field(default=None, max_length=120)
class DocumentUploadCreateRequest(BaseModel):
    business_id: UUID
    uploader_id: UUID | None = None
    document_type: str = Field(min_length=1, max_length=120)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=120)
    storage_bucket: str = Field(min_length=1, max_length=120)
    storage_key: str = Field(min_length=1, max_length=255)
    status: DocumentUploadStatus | None = None
    ocr_status: DocumentOCRStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)
    metadata: dict[str, Any] | None = None


class DocumentUploadResponse(_ORMBaseModel):
    id: UUID
    business_id: UUID
    uploader_id: UUID | None
    permit_id: UUID | None
    file_name: str
    file_url: AnyUrl
    content_type: str | None
    storage_bucket: str | None
    ocr_status: DocumentProcessingStatus
    requirement_key: str | None
    ocr_confidence: float | None
    ocr_text: str | None
    external_reference: str | None
    document_type: str
    filename: str
    content_type: str | None
    storage_bucket: str
    storage_key: str
    status: DocumentUploadStatus
    ocr_status: DocumentOCRStatus
    ocr_text: str | None
    ocr_metadata: dict[str, Any] | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PermitResponse(_ORMBaseModel):
    id: UUID
    business_id: UUID
    permit_number: str
    permit_type: str
    jurisdiction: str | None
    issued_at: datetime | None
    expires_at: datetime | None
    status: PermitStatus
    metadata: dict | None
    created_at: datetime
    updated_at: datetime


class ReadinessRequirement(BaseModel):
    name: str
    description: str | None = None
    name: str
    permit_type: str
    permit_number: str | None
    issuing_authority: str | None
    jurisdiction: str | None
    status: PermitStatus
    issued_on: datetime | None
    expires_on: datetime | None
    webhook_url: str | None
    last_webhook_at: datetime | None
    document_id: UUID | None
    metadata: dict[str, Any] | None


class BusinessReadinessChecklistItem(BaseModel):
    slug: str
    title: str
    description: str
    status: str
    completed_at: datetime | None = None


class BusinessReadinessResponse(BaseModel):
    business_id: UUID
    readiness_score: float
    requirements: list[ReadinessRequirement]
    next_actions: list[str]
    permit_ids: list[UUID]
    last_updated: datetime
    business_name: str
    readiness_score: float = Field(ge=0.0, le=1.0)
    readiness_stage: str
    checklist: list[BusinessReadinessChecklistItem]
    gating_requirements: list[str]
    outstanding_actions: list[str]
    last_evaluated_at: datetime


class CheckoutLineItem(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    amount_cents: int = Field(gt=0)
    category: str | None = Field(default=None, max_length=120)


class CheckoutRequest(BaseModel):
    business_id: UUID
    booking_id: UUID | None = None
    currency: str = Field(min_length=3, max_length=3)
    line_items: list[CheckoutLineItem]
    initiate_refund: bool = False
    payment_id: UUID | None = None

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return normalized.lower()


class CheckoutResponse(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    total_amount_cents: int
    currency: str
    client_secret: str | None = None
    receipt_url: AnyUrl | None = None
    refunded_amount_cents: int | None = None
    amount: int = Field(ge=0, description="Amount in the smallest currency unit")
    quantity: int = Field(default=1, ge=1)
    taxable: bool = False
    refundable: bool = True


class CheckoutPaymentCreateRequest(BaseModel):
    currency: str = Field(min_length=3, max_length=3)
    line_items: Sequence[CheckoutLineItem]
    business_id: UUID | None = None
    booking_id: UUID | None = None
    metadata: dict[str, Any] | None = None
    requirements_gate: bool = False
    minimum_readiness_score: float = Field(default=0.6, ge=0.0, le=1.0)
    action: str = Field(default="confirm", pattern="^(confirm|refund)$")
    existing_payment_id: UUID | None = None
    refund_reason: str | None = Field(default=None, max_length=255)

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return normalized


class CheckoutPaymentResponse(_ORMBaseModel):
    id: UUID
    business_id: UUID | None
    booking_id: UUID | None
    status: CheckoutPaymentStatus
    currency: str
    total_amount: float
    line_items: list[dict[str, Any]]
    payment_provider: str
    provider_reference: str | None
    receipt_url: str | None
    metadata: dict[str, Any] | None
    refund_reason: str | None
    refund_requested_at: datetime | None
    refunded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PaymentIntentCreateRequest(BaseModel):
    booking_id: UUID
    amount: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return normalized.lower()


class PaymentIntentResponse(BaseModel):
    client_secret: str = Field(min_length=1)


class SubleaseContractSendRequest(BaseModel):
    booking_id: UUID
    signer_email: EmailStr
    signer_name: str | None = Field(default=None, max_length=255)
    return_url: AnyUrl | None = None


class SubleaseContractSendResponse(BaseModel):
    booking_id: UUID
    envelope_id: str = Field(min_length=1)
    sign_url: str = Field(min_length=1)


class SubleaseContractStatusResponse(BaseModel):
    booking_id: UUID
    envelope_id: str = Field(min_length=1)
    status: SubleaseContractStatus
    sign_url: str | None
    document_s3_bucket: str | None
    document_s3_key: str | None
    completed_at: datetime | None
    last_checked_at: datetime | None


def serialize_user(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


class APIKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    expires_at: datetime | None = None


class APIKeyResponse(_ORMBaseModel):
    id: UUID
    name: str
    key_prefix: str
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    rotated_at: datetime | None
    created_at: datetime


class APIKeyWithSecretResponse(APIKeyResponse):
    secret: str


def serialize_api_key(api_key: APIKey) -> APIKeyResponse:
    return APIKeyResponse.model_validate(api_key)


def serialize_kitchen(kitchen: Kitchen) -> KitchenResponse:
    return KitchenResponse.model_validate(kitchen)


def serialize_booking(booking: Booking) -> BookingResponse:
    return BookingResponse.model_validate(booking)


def serialize_review(review: Review) -> ReviewResponse:
    return ReviewResponse.model_validate(review)


def serialize_compliance_document(document: ComplianceDocument) -> ComplianceDocumentResponse:
    return ComplianceDocumentResponse.model_validate(document)


def serialize_document_upload(document: DocumentUpload) -> DocumentUploadResponse:
    return DocumentUploadResponse.model_validate(document)


def serialize_permit(permit: BusinessPermit) -> PermitResponse:
    return PermitResponse.model_validate(permit)
def serialize_document_upload(upload: DocumentUpload) -> DocumentUploadResponse:
    return DocumentUploadResponse.model_validate(upload)


def serialize_permit(permit: Permit) -> PermitResponse:
    return PermitResponse.model_validate(permit)


def serialize_checkout_payment(payment: CheckoutPayment) -> CheckoutPaymentResponse:
    return CheckoutPaymentResponse.model_validate(payment)
