"""Pydantic schemas powering the core platform API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import Request
from pydantic import AnyUrl, BaseModel, ConfigDict, EmailStr, Field, field_validator

from prep.models.orm import (
    Booking,
    BookingStatus,
    ComplianceDocument,
    ComplianceDocumentStatus,
    Kitchen,
    Review,
    SubleaseContractStatus,
    User,
    UserRole,
)


class _ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    """Standardized description of an API error."""

    code: str = Field(description="Machine-readable error identifier")
    message: str = Field(description="Human readable explanation of the failure")
    field: str | None = Field(
        default=None, description="Optional field name that triggered the error"
    )


class ErrorResponseEnvelope(BaseModel):
    """Canonical envelope for API error responses."""

    request_id: str = Field(description="Correlated identifier for this request")
    error: ErrorDetail
    meta: dict[str, Any] | None = Field(
        default=None, description="Optional metadata describing the error context"
    )


def resolve_request_id(request: Request) -> str:
    """Derive or create a stable request identifier for downstream logging."""

    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, str) and existing:
        return existing

    header_id = request.headers.get("x-request-id") or request.headers.get(
        "x-correlation-id"
    )
    request_id = header_id or str(uuid4())
    request.state.request_id = request_id
    return request_id


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


class CursorPagination(BaseModel):
    """Cursor-based pagination metadata."""

    limit: int = Field(ge=1, le=100, description="Maximum number of records returned")
    cursor: datetime | None = Field(
        default=None,
        description="Cursor supplied by the client for this page",
    )
    next_cursor: datetime | None = Field(
        default=None,
        description="Cursor to request the next page of results",
    )
    total: int = Field(ge=0, description="Total records available for the query")


class ReviewCollectionResponse(BaseModel):
    """Paginated container for kitchen reviews."""

    items: list[ReviewResponse]
    pagination: CursorPagination


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
