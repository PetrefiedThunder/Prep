"""Domain models describing the Codex marketplace."""

from __future__ import annotations

import enum
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampedMixin


class UserRole(str, enum.Enum):
    """Supported roles within the Codex platform."""

    ADMIN = "admin"
    HOST = "host"
    CUSTOMER = "customer"


class BookingStatus(str, enum.Enum):
    """Lifecycle states for bookings."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class User(Base, TimestampedMixin):
    """End user of the Codex platform."""

    __tablename__ = "codex_users"

    id: Mapped[Uuid] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.CUSTOMER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    kitchens: Mapped[list[Kitchen]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    bookings: Mapped[list[Booking]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        foreign_keys="Booking.customer_id",
    )
    hosted_bookings: Mapped[list[Booking]] = relationship(
        back_populates="host",
        cascade="all, delete-orphan",
        foreign_keys="Booking.host_id",
    )


class Kitchen(Base, TimestampedMixin):
    """Commercial kitchen listed on Codex."""

    __tablename__ = "codex_kitchens"

    id: Mapped[Uuid] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[Uuid] = mapped_column(
        Uuid, ForeignKey("codex_users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(60), nullable=False)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped[User] = relationship(back_populates="kitchens")
    bookings: Mapped[list[Booking]] = relationship(
        back_populates="kitchen", cascade="all, delete-orphan"
    )


class Booking(Base, TimestampedMixin):
    """Customer booking for a specific kitchen."""

    __tablename__ = "codex_bookings"

    id: Mapped[Uuid] = mapped_column(Uuid, primary_key=True, default=uuid4)
    kitchen_id: Mapped[Uuid] = mapped_column(
        Uuid, ForeignKey("codex_kitchens.id", ondelete="CASCADE"), nullable=False
    )
    host_id: Mapped[Uuid] = mapped_column(
        Uuid, ForeignKey("codex_users.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[Uuid] = mapped_column(
        Uuid, ForeignKey("codex_users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), nullable=False, default=BookingStatus.PENDING
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    kitchen: Mapped[Kitchen] = relationship(back_populates="bookings")
    host: Mapped[User] = relationship(back_populates="hosted_bookings", foreign_keys=[host_id])
    customer: Mapped[User] = relationship(back_populates="bookings", foreign_keys=[customer_id])

    def duration(self) -> timedelta:
        """Return the booking duration."""

        return self.end_time - self.start_time


__all__ = [
    "Booking",
    "BookingStatus",
    "Kitchen",
    "User",
    "UserRole",
]
