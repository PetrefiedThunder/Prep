"""SQLAlchemy ORM models backing the Prep admin dashboard."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import enum

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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


class User(Base, TimestampedMixin):
    """Represents an end user of the Prep platform."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    kitchens: Mapped[list["Kitchen"]] = relationship(back_populates="host")


class Kitchen(Base, TimestampedMixin):
    """Commercial kitchen listed on the marketplace."""

    __tablename__ = "kitchens"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    host_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(60), nullable=True)
    hourly_rate: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(50), default="pending")
    certification_status: Mapped[str] = mapped_column(String(50), default="pending_review")
    published: Mapped[bool] = mapped_column(Boolean, default=False)

    host: Mapped[User] = relationship(back_populates="kitchens")
    certifications: Mapped[list["CertificationDocument"]] = relationship(back_populates="kitchen")
    moderation_events: Mapped[list["KitchenModerationEvent"]] = relationship(
        back_populates="kitchen", cascade="all, delete-orphan", order_by="KitchenModerationEvent.created_at.desc()"
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

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    host_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    customer_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    kitchen_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("kitchens.id"), index=True)
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


class Review(Base, TimestampedMixin):
    """Guest review for a completed booking."""

    __tablename__ = "reviews"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bookings.id"), index=True)
    kitchen_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("kitchens.id"), index=True)
    host_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    customer_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    booking: Mapped[Booking] = relationship(back_populates="reviews")
    kitchen: Mapped[Kitchen] = relationship()
    host: Mapped[User] = relationship(foreign_keys=[host_id])
    customer: Mapped[User] = relationship(foreign_keys=[customer_id])


class OperationalExpense(Base, TimestampedMixin):
    """Operational expenses used for financial analytics."""

    __tablename__ = "operational_expenses"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    category: Mapped[str] = mapped_column(String(120))
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    incurred_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class KitchenModerationEvent(Base):
    """Audit trail capturing moderation decisions for a kitchen."""

    __tablename__ = "kitchen_moderation_events"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("kitchens.id"), index=True)
    admin_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    kitchen: Mapped[Kitchen] = relationship(back_populates="moderation_events")
    admin: Mapped[User] = relationship()


class CertificationDocument(Base, TimestampedMixin):
    """Uploaded certification or inspection document."""

    __tablename__ = "certification_documents"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("kitchens.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    file_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    kitchen: Mapped[Kitchen] = relationship(back_populates="certifications")

