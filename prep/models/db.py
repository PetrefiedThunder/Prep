"""SQLAlchemy models backing the Prep admin dashboard."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from prep.models.guid import GUID


class Base(DeclarativeBase):
    """Declarative base class."""

    pass


class UserRole(str, enum.Enum):
    """Supported user roles within the Prep platform."""

    HOST = "host"
    ADMIN = "admin"
    CUSTOMER = "customer"


class ModerationStatus(str, enum.Enum):
    """Workflow state for kitchen moderation."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class CertificationReviewStatus(str, enum.Enum):
    """Possible review states for certification documents."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    """Application user model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.HOST)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    suspension_reason: Mapped[Optional[str]] = mapped_column(String(255))
    suspended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    kitchens: Mapped[List["Kitchen"]] = relationship(back_populates="owner")
    reviews: Mapped[List["CertificationDocument"]] = relationship(
        back_populates="reviewer", foreign_keys="CertificationDocument.reviewer_id"
    )


class Kitchen(Base):
    """Commercial kitchen listed on the platform."""

    __tablename__ = "kitchens"
    __table_args__ = (
        CheckConstraint("trust_score >= 0 AND trust_score <= 5", name="ck_kitchen_trust_score_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text())
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    moderation_status: Mapped[ModerationStatus] = mapped_column(
        Enum(ModerationStatus), nullable=False, index=True, default=ModerationStatus.PENDING
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text())
    trust_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    hourly_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    certification_status: Mapped[CertificationReviewStatus] = mapped_column(
        Enum(CertificationReviewStatus), nullable=False, index=True, default=CertificationReviewStatus.PENDING
    )

    owner: Mapped[User] = relationship(back_populates="kitchens")
    certifications: Mapped[List["CertificationDocument"]] = relationship(
        back_populates="kitchen", cascade="all, delete-orphan"
    )


class CertificationDocument(Base):
    """Uploaded certification documents for kitchens."""

    __tablename__ = "certification_documents"
    __table_args__ = (
        UniqueConstraint("kitchen_id", "document_type", name="uq_kitchen_document_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(120), nullable=False)
    document_url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[CertificationReviewStatus] = mapped_column(
        Enum(CertificationReviewStatus), nullable=False, index=True, default=CertificationReviewStatus.PENDING
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    kitchen: Mapped[Kitchen] = relationship(back_populates="certifications")
    reviewer: Mapped[Optional[User]] = relationship(back_populates="reviews")
