"""Pydantic schemas powering the core platform API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from prep.models.orm import (
    Booking,
    BookingStatus,
    ComplianceDocument,
    ComplianceDocumentStatus,
    Kitchen,
    Review,
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
