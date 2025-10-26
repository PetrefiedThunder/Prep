"""SQLAlchemy ORM models backing the Prep admin dashboard."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import enum

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
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from prep.models.guid import GUID


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class TimestampedMixin:
    """Reusable mixin providing created/updated timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class UserRole(str, enum.Enum):
    """Platform roles supported by the Prep platform."""

    ADMIN = "admin"
    HOST = "host"
    CUSTOMER = "customer"


class User(Base, TimestampedMixin):
    """Represents an end user of the Prep platform."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.CUSTOMER, nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    kitchens: Mapped[list["Kitchen"]] = relationship(back_populates="host")
    matching_preference: Mapped[UserMatchingPreference | None] = relationship(
        back_populates="user", uselist=False
    )


class Kitchen(Base, TimestampedMixin):
    """Commercial kitchen listed on the marketplace."""

    __tablename__ = "kitchens"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    host_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(60), nullable=True)
    hourly_rate: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(50), default="pending")
    certification_status: Mapped[str] = mapped_column(String(50), default="pending_review")
    published: Mapped[bool] = mapped_column(Boolean, default=False)

    host: Mapped[User] = relationship(back_populates="kitchens")
    certifications: Mapped[list["CertificationDocument"]] = relationship(back_populates="kitchen")
    compliance_documents: Mapped[list["ComplianceDocument"]] = relationship(
        back_populates="kitchen", cascade="all, delete-orphan"
    )
    moderation_events: Mapped[list["KitchenModerationEvent"]] = relationship(
        back_populates="kitchen", cascade="all, delete-orphan", order_by="KitchenModerationEvent.created_at.desc()"
    )
    matching_profile: Mapped[KitchenMatchingProfile | None] = relationship(
        back_populates="kitchen", uselist=False
    )


class BookingStatus(str, enum.Enum):
    """State transitions for bookings."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Booking(Base, TimestampedMixin):
    """Represents a customer booking for a kitchen."""

    __tablename__ = "bookings"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    host_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    customer_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    kitchen_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("kitchens.id"), index=True)
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), nullable=False, default=BookingStatus.PENDING)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    platform_fee: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    host_payout_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    payment_method: Mapped[str] = mapped_column(String(50), default="card")
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)

    kitchen: Mapped[Kitchen] = relationship()
    host: Mapped[User] = relationship(foreign_keys=[host_id])
    customer: Mapped[User] = relationship(foreign_keys=[customer_id])
    reviews: Mapped[list["Review"]] = relationship(back_populates="booking")


class ReviewStatus(str, enum.Enum):
    """Lifecycle state for user reviews."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewFlagStatus(str, enum.Enum):
    """Workflow status for review moderation flags."""

    OPEN = "open"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class Review(Base, TimestampedMixin):
    """Guest review for a completed booking."""

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("booking_id", "customer_id", name="uq_review_booking_customer"),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("bookings.id"), index=True)
    kitchen_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("kitchens.id"), index=True)
    host_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    customer_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    equipment_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    cleanliness_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    communication_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    value_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), nullable=False, default=ReviewStatus.PENDING
    )
    spam_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    moderated_by: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    host_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    host_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    booking: Mapped[Booking] = relationship(back_populates="reviews")
    kitchen: Mapped[Kitchen] = relationship()
    host: Mapped[User] = relationship(foreign_keys=[host_id])
    customer: Mapped[User] = relationship(foreign_keys=[customer_id])
    photos: Mapped[list["ReviewPhoto"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
    votes: Mapped[list["ReviewVote"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
    flags: Mapped[list["ReviewFlag"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )


class ComplianceDocumentStatus(str, enum.Enum):
    """Workflow states for uploaded compliance documentation."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ComplianceDocument(Base, TimestampedMixin):
    """Compliance paperwork that kitchens must maintain."""

    __tablename__ = "compliance_documents"
    __table_args__ = (
        UniqueConstraint("kitchen_id", "document_type", name="uq_compliance_document"),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("kitchens.id"), index=True)
    uploader_id: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    document_type: Mapped[str] = mapped_column(String(120), nullable=False)
    document_url: Mapped[str] = mapped_column(String(512), nullable=False)
    verification_status: Mapped[ComplianceDocumentStatus] = mapped_column(
        Enum(ComplianceDocumentStatus), default=ComplianceDocumentStatus.PENDING, nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_id: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    kitchen: Mapped[Kitchen] = relationship(back_populates="compliance_documents")
    uploader: Mapped[User | None] = relationship(foreign_keys=[uploader_id])
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewer_id])


class OperationalExpense(Base, TimestampedMixin):
    """Operational expenses used for financial analytics."""

    __tablename__ = "operational_expenses"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    category: Mapped[str] = mapped_column(String(120))
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    incurred_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class KitchenModerationEvent(Base):
    """Audit trail capturing moderation decisions for a kitchen."""

    __tablename__ = "kitchen_moderation_events"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("kitchens.id"), index=True)
    admin_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    kitchen: Mapped[Kitchen] = relationship(back_populates="moderation_events")
    admin: Mapped[User] = relationship()


class UserMatchingPreference(Base, TimestampedMixin):
    """Stores matching preferences specified by a user."""

    __tablename__ = "user_matching_preferences"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), primary_key=True
    )
    equipment: Mapped[list[str]] = mapped_column(JSON, default=list)
    certifications: Mapped[list[str]] = mapped_column(JSON, default=list)
    cuisines: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_cities: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_states: Mapped[list[str]] = mapped_column(JSON, default=list)
    availability: Mapped[list[str]] = mapped_column(JSON, default=list)
    min_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    preference_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="matching_preference")


class KitchenMatchingProfile(Base, TimestampedMixin):
    """Extended feature data powering the smart matching engine."""

    __tablename__ = "kitchen_matching_profiles"

    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id"), primary_key=True
    )
    equipment: Mapped[list[str]] = mapped_column(JSON, default=list)
    certifications: Mapped[list[str]] = mapped_column(JSON, default=list)
    cuisines: Mapped[list[str]] = mapped_column(JSON, default=list)
    availability: Mapped[list[str]] = mapped_column(JSON, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_hourly_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_hourly_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    kitchen: Mapped[Kitchen] = relationship(back_populates="matching_profile")


class KitchenExternalRating(Base, TimestampedMixin):
    """External rating data sourced from third-party review platforms."""

    __tablename__ = "kitchen_external_ratings"
    __table_args__ = (
        UniqueConstraint("kitchen_id", "source", name="uq_external_rating_source"),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id"), index=True
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    rating_scale: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    rating_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    normalized_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    kitchen: Mapped[Kitchen] = relationship()


class KitchenRatingHistory(Base):
    """Historical snapshots of external rating syncs for trend analysis."""

    __tablename__ = "kitchen_rating_history"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id"), index=True
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating_scale: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    rating_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    normalized_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    kitchen: Mapped[Kitchen] = relationship()


class KitchenSentimentTrend(Base):
    """Aggregated sentiment analysis windows for external reviews."""

    __tablename__ = "kitchen_sentiment_trends"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("kitchens.id"), nullable=True, index=True
    )
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    average_score: Mapped[float] = mapped_column(Float, nullable=False)
    positive_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    neutral_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    negative_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    kitchen: Mapped[Kitchen | None] = relationship()


class CertificationDocument(Base, TimestampedMixin):
    """Uploaded certification or inspection document."""

    __tablename__ = "certification_documents"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("kitchens.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    file_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    kitchen: Mapped[Kitchen] = relationship(back_populates="certifications")


class ReviewPhoto(Base):
    """User supplied media attached to a review."""

    __tablename__ = "review_photos"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    review_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("reviews.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    review: Mapped[Review] = relationship(back_populates="photos")


class ReviewVote(Base):
    """Stores whether a user found a review helpful."""

    __tablename__ = "review_votes"
    __table_args__ = (
        UniqueConstraint("review_id", "user_id", name="uq_review_vote_user"),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    review_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("reviews.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    is_helpful: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    review: Mapped[Review] = relationship(back_populates="votes")
    user: Mapped[User] = relationship()


class ReviewFlag(Base, TimestampedMixin):
    """Moderation flag raised against a review."""

    __tablename__ = "review_flags"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    review_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("reviews.id", ondelete="CASCADE"), index=True
    )
    reporter_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReviewFlagStatus] = mapped_column(
        Enum(ReviewFlagStatus), nullable=False, default=ReviewFlagStatus.OPEN
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True
    )

    review: Mapped[Review] = relationship(back_populates="flags")
    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id])

