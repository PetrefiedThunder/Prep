from __future__ import annotations

import enum
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, List
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, relationship
from sqlalchemy.sql.sqltypes import Date

try:  # pragma: no cover - import locations vary across SQLAlchemy versions
    from sqlalchemy import UniqueConstraint
except ImportError:  # pragma: no cover - fallback for stripped-down builds
    try:
        from sqlalchemy.sql.schema import UniqueConstraint  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - final fallback for tests without SQLAlchemy
        class UniqueConstraint:  # type: ignore[override]
            def __init__(self, *args, **kwargs) -> None:
                self.args = args
                self.kwargs = kwargs

from .guid import GUID


class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore[override]
        import re

        name = cls.__name__
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    HOST = "host"
    CUSTOMER = "customer"


class ModerationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class CertificationReviewStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    RENEWAL_REQUESTED = "renewal_requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewFlagStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class ComplianceDocumentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class VerificationTaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
class SubleaseContractStatus(str, enum.Enum):
    CREATED = "created"
    SENT = "sent"
    COMPLETED = "completed"
    DECLINED = "declined"
    VOIDED = "voided"
    ERROR = "error"


class DeliveryProvider(str, enum.Enum):
    DOORDASH = "doordash"
    UBER = "uber"


class DeliveryStatus(str, enum.Enum):
    CREATED = "created"
    DISPATCHED = "dispatched"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False, default="hashed"
    )
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    stripe_account_id: Mapped[str | None] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    suspension_reason: Mapped[str | None] = mapped_column(Text)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    kitchens: Mapped[List["Kitchen"]] = relationship(
        "Kitchen", back_populates="host", cascade="all, delete-orphan"
    )
    bookings: Mapped[List["Booking"]] = relationship(
        "Booking",
        back_populates="customer",
        cascade="all, delete-orphan",
        foreign_keys="Booking.customer_id",
    )
    hosted_bookings: Mapped[List["Booking"]] = relationship(
        "Booking",
        back_populates="host",
        cascade="all, delete-orphan",
        foreign_keys="Booking.host_id",
    )
    reviews_authored: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="customer",
        cascade="all, delete-orphan",
        foreign_keys="Review.customer_id",
    )
    reviews_received: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="host",
        cascade="all, delete-orphan",
        foreign_keys="Review.host_id",
    )
    moderation_events: Mapped[List["KitchenModerationEvent"]] = relationship(
        "KitchenModerationEvent",
        back_populates="admin",
        cascade="all, delete-orphan",
        foreign_keys="KitchenModerationEvent.admin_id",
    )


class Kitchen(TimestampMixin, Base):
    __tablename__ = "kitchens"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    host_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(60))
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    trust_score: Mapped[float | None] = mapped_column(Float)
    pricing: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    equipment: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    moderation_status: Mapped[ModerationStatus] = mapped_column(
        Enum(ModerationStatus), default=ModerationStatus.PENDING, nullable=False
    )
    certification_status: Mapped[CertificationReviewStatus] = mapped_column(
        Enum(CertificationReviewStatus), default=CertificationReviewStatus.PENDING, nullable=False
    )
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    compliance_status: Mapped[str | None] = mapped_column(String(32), default="unknown")
    risk_score: Mapped[int | None] = mapped_column(Integer)
    last_compliance_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    health_permit_number: Mapped[str | None] = mapped_column(String(120))
    last_inspection_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    insurance_info: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    zoning_type: Mapped[str | None] = mapped_column(String(120))

    host: Mapped[User] = relationship("User", back_populates="kitchens")
    bookings: Mapped[List["Booking"]] = relationship(
        "Booking", back_populates="kitchen", cascade="all, delete-orphan"
    )
    reviews: Mapped[List["Review"]] = relationship(
        "Review", back_populates="kitchen", cascade="all, delete-orphan"
    )
    certifications: Mapped[List["CertificationDocument"]] = relationship(
        "CertificationDocument", back_populates="kitchen", cascade="all, delete-orphan"
    )
    moderation_events: Mapped[List["KitchenModerationEvent"]] = relationship(
        "KitchenModerationEvent", back_populates="kitchen", cascade="all, delete-orphan"
    )
    compliance_documents: Mapped[List["ComplianceDocument"]] = relationship(
        "ComplianceDocument", back_populates="kitchen", cascade="all, delete-orphan"
    )
    recurring_templates: Mapped[List["RecurringBookingTemplate"]] = relationship(
        "RecurringBookingTemplate", back_populates="kitchen", cascade="all, delete-orphan"
    )


class ChecklistTemplate(TimestampMixin, Base):
    """Versioned JSON schema used to power dynamic admin checklists."""

    __tablename__ = "checklist_templates"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_checklist_template_name_version"),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    host_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    host_payout_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    payment_method: Mapped[str] = mapped_column(String(50), default="card", nullable=False)
    payment_intent_id: Mapped[str | None] = mapped_column(String(255))
    paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str | None] = mapped_column(String(120))
    cancellation_reason: Mapped[str | None] = mapped_column(String(255))
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255))

    kitchen: Mapped[Kitchen] = relationship("Kitchen", back_populates="bookings")
    host: Mapped[User] = relationship(
        "User", back_populates="hosted_bookings", foreign_keys=[host_id]
    )
    customer: Mapped[User] = relationship(
        "User", back_populates="bookings", foreign_keys=[customer_id]
    )
    reviews: Mapped[List["Review"]] = relationship(
        "Review", back_populates="booking", cascade="all, delete-orphan"
    )
    sublease_contract: Mapped["SubleaseContract" | None] = relationship(
        "SubleaseContract", back_populates="booking", uselist=False
    )


class StripeWebhookEvent(TimestampMixin, Base):
    __tablename__ = "stripe_webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class RecurringBookingTemplate(TimestampMixin, Base):
    __tablename__ = "recurring_booking_templates"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    host_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rrule: Mapped[str] = mapped_column(Text, nullable=False)
    buffer_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    kitchen: Mapped[Kitchen] = relationship("Kitchen", back_populates="recurring_templates")
    host: Mapped[User] = relationship("User", foreign_keys=[host_id])
    customer: Mapped[User] = relationship("User", foreign_keys=[customer_id])


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False
    )
    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    host_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    equipment_rating: Mapped[float | None] = mapped_column(Float)
    cleanliness_rating: Mapped[float | None] = mapped_column(Float)
    communication_rating: Mapped[float | None] = mapped_column(Float)
    value_rating: Mapped[float | None] = mapped_column(Float)
    comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False
    )
    spam_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    moderated_by: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    host_response: Mapped[str | None] = mapped_column(Text)
    host_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    booking: Mapped[Booking] = relationship("Booking", back_populates="reviews")
    kitchen: Mapped[Kitchen] = relationship("Kitchen", back_populates="reviews")
    host: Mapped[User] = relationship(
        "User", back_populates="reviews_received", foreign_keys=[host_id]
    )
    customer: Mapped[User] = relationship(
        "User", back_populates="reviews_authored", foreign_keys=[customer_id]
    )
    photos: Mapped[List["ReviewPhoto"]] = relationship(
        "ReviewPhoto", back_populates="review", cascade="all, delete-orphan"
    )
    votes: Mapped[List["ReviewVote"]] = relationship(
        "ReviewVote", back_populates="review", cascade="all, delete-orphan"
    )
    flags: Mapped[List["ReviewFlag"]] = relationship(
        "ReviewFlag", back_populates="review", cascade="all, delete-orphan"
    )


class ReviewPhoto(TimestampMixin, Base):
    __tablename__ = "review_photos"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    review_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    review: Mapped[Review] = relationship("Review", back_populates="photos")


class ReviewVote(TimestampMixin, Base):
    __tablename__ = "review_votes"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    review_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    is_helpful: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    review: Mapped[Review] = relationship("Review", back_populates="votes")
    voter: Mapped[User] = relationship("User")


class ReviewFlag(TimestampMixin, Base):
    __tablename__ = "review_flags"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    review_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    reporter_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReviewFlagStatus] = mapped_column(
        Enum(ReviewFlagStatus), default=ReviewFlagStatus.OPEN, nullable=False
    )
    admin_id: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    review: Mapped[Review] = relationship("Review", back_populates="flags")
    reporter: Mapped[User] = relationship("User", foreign_keys=[reporter_id])
    admin: Mapped[User | None] = relationship("User", foreign_keys=[admin_id])


class CertificationDocument(TimestampMixin, Base):
    __tablename__ = "certification_documents"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(120), nullable=False)
    document_url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[CertificationReviewStatus] = mapped_column(
        Enum(CertificationReviewStatus), default=CertificationReviewStatus.PENDING, nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_id: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    kitchen: Mapped[Kitchen] = relationship("Kitchen", back_populates="certifications")
    reviewer: Mapped[User | None] = relationship("User")


class KitchenModerationEvent(TimestampMixin, Base):
    __tablename__ = "kitchen_moderation_events"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    admin_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    kitchen: Mapped[Kitchen] = relationship("Kitchen", back_populates="moderation_events")
    admin: Mapped[User] = relationship("User", back_populates="moderation_events")


class ComplianceDocument(TimestampMixin, Base):
    __tablename__ = "compliance_documents"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    uploader_id: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    reviewer_id: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    document_type: Mapped[str] = mapped_column(String(120), nullable=False)
    document_url: Mapped[str] = mapped_column(String(512), nullable=False)
    verification_status: Mapped[ComplianceDocumentStatus] = mapped_column(
        Enum(ComplianceDocumentStatus), default=ComplianceDocumentStatus.PENDING, nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    kitchen: Mapped[Kitchen] = relationship(
        "Kitchen", back_populates="compliance_documents"
    )
    uploader: Mapped[User | None] = relationship("User", foreign_keys=[uploader_id])
    reviewer: Mapped[User | None] = relationship("User", foreign_keys=[reviewer_id])


class SubleaseContract(TimestampMixin, Base):
    __tablename__ = "sublease_contracts"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    envelope_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[SubleaseContractStatus] = mapped_column(
        Enum(SubleaseContractStatus), default=SubleaseContractStatus.CREATED, nullable=False
    )
    signer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    signer_name: Mapped[str | None] = mapped_column(String(255))
    sign_url: Mapped[str | None] = mapped_column(String(512))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    document_s3_bucket: Mapped[str | None] = mapped_column(String(255))
    document_s3_key: Mapped[str | None] = mapped_column(String(512))

    booking: Mapped[Booking] = relationship(
        "Booking", back_populates="sublease_contract", passive_deletes=True
    )


class COIDocument(TimestampMixin, Base):
    __tablename__ = "coi_documents"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy_number: Mapped[str | None] = mapped_column(String(128))
    insured_name: Mapped[str | None] = mapped_column(String(255))
    validation_errors: Mapped[str | None] = mapped_column(Text)


class VerificationTask(TimestampMixin, Base):
    __tablename__ = "verification_tasks"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(GUID(), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[VerificationTaskStatus] = mapped_column(
        Enum(VerificationTaskStatus), default=VerificationTaskStatus.PENDING, nullable=False
    )
    assigned_to: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assignee: Mapped[User | None] = relationship("User")

class OperationalExpense(TimestampMixin, Base):
    __tablename__ = "operational_expenses"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    incurred_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    category: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)


class RegDoc(Base):
    """Normalized regulatory documents stored for analytics."""

    __tablename__ = "reg_docs"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    jurisdiction: Mapped[str] = mapped_column(String(255), nullable=False)
    code_section: Mapped[str] = mapped_column(String(120), nullable=False)
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date)
    citation_url: Mapped[str | None] = mapped_column(Text)
    sha256_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    inserted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class DeliveryOrder(TimestampMixin, Base):
    __tablename__ = "delivery_orders"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("bookings.id", ondelete="SET NULL")
    )
    external_order_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    provider: Mapped[DeliveryProvider] = mapped_column(
        Enum(DeliveryProvider), nullable=False
    )
    provider_delivery_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus), default=DeliveryStatus.CREATED, nullable=False
    )
    pickup_address: Mapped[str] = mapped_column(String(512), nullable=False)
    dropoff_address: Mapped[str] = mapped_column(String(512), nullable=False)
    dropoff_contact: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tracking_url: Mapped[str | None] = mapped_column(String(512))
    courier_name: Mapped[str | None] = mapped_column(String(255))
    courier_phone: Mapped[str | None] = mapped_column(String(64))
    proof_photo_url: Mapped[str | None] = mapped_column(String(512))
    proof_signature: Mapped[str | None] = mapped_column(Text)
    last_status_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    booking: Mapped["Booking" | None] = relationship("Booking")
    status_events: Mapped[List["DeliveryStatusEvent"]] = relationship(
        "DeliveryStatusEvent",
        back_populates="delivery",
        cascade="all, delete-orphan",
        order_by="DeliveryStatusEvent.occurred_at",
    )
    compliance_events: Mapped[List["DeliveryComplianceEvent"]] = relationship(
        "DeliveryComplianceEvent",
        back_populates="delivery",
        cascade="all, delete-orphan",
        order_by="DeliveryComplianceEvent.occurred_at",
    )


class DeliveryStatusEvent(TimestampMixin, Base):
    __tablename__ = "delivery_status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    delivery_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("delivery_orders.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[DeliveryStatus] = mapped_column(Enum(DeliveryStatus), nullable=False)
    provider_status: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)

    delivery: Mapped[DeliveryOrder] = relationship("DeliveryOrder", back_populates="status_events")


class DeliveryComplianceEvent(TimestampMixin, Base):
    __tablename__ = "delivery_compliance_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    delivery_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("delivery_orders.id", ondelete="CASCADE"), nullable=False
    )
    courier_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_reference: Mapped[str | None] = mapped_column(String(255))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)

    delivery: Mapped[DeliveryOrder] = relationship("DeliveryOrder", back_populates="compliance_events")


__all__ = [
    "Base",
    "Booking",
    "BookingStatus",
    "VerificationTask",
    "VerificationTaskStatus",
    "CertificationDocument",
    "CertificationReviewStatus",
    "ComplianceDocument",
    "ComplianceDocumentStatus",
    "SubleaseContract",
    "SubleaseContractStatus",
    "Kitchen",
    "KitchenModerationEvent",
    "ModerationStatus",
    "Review", 
    "ReviewFlag", 
    "ReviewFlagStatus", 
    "ReviewPhoto", 
    "ReviewStatus", 
    "ReviewVote", 
    "RegDoc",
    "User",
    "UserRole",
    "COIDocument",
    "DeliveryOrder",
    "DeliveryStatusEvent",
    "DeliveryComplianceEvent",
    "DeliveryStatus",
    "DeliveryProvider",
]
