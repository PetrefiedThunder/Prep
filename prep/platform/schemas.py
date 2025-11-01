"""Pydantic schemas powering the core platform API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence
from uuid import UUID

from pydantic import AnyUrl, BaseModel, ConfigDict, EmailStr, Field
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from prep.models.orm import (
    Booking,
    BookingStatus,
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


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class AuthenticatedUserResponse(AuthTokenResponse):
    user: UserResponse


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
    business_name: str
    readiness_score: float = Field(ge=0.0, le=1.0)
    readiness_stage: str
    checklist: list[BusinessReadinessChecklistItem]
    gating_requirements: list[str]
    outstanding_actions: list[str]
    last_evaluated_at: datetime


class CheckoutLineItem(BaseModel):
    name: str = Field(min_length=1, max_length=255)
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


def serialize_kitchen(kitchen: Kitchen) -> KitchenResponse:
    return KitchenResponse.model_validate(kitchen)


def serialize_booking(booking: Booking) -> BookingResponse:
    return BookingResponse.model_validate(booking)


def serialize_review(review: Review) -> ReviewResponse:
    return ReviewResponse.model_validate(review)


def serialize_compliance_document(document: ComplianceDocument) -> ComplianceDocumentResponse:
    return ComplianceDocumentResponse.model_validate(document)


def serialize_document_upload(upload: DocumentUpload) -> DocumentUploadResponse:
    return DocumentUploadResponse.model_validate(upload)


def serialize_permit(permit: Permit) -> PermitResponse:
    return PermitResponse.model_validate(permit)


def serialize_checkout_payment(payment: CheckoutPayment) -> CheckoutPaymentResponse:
    return CheckoutPaymentResponse.model_validate(payment)
