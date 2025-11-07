from __future__ import annotations

import enum
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, relationship

Date = DateTime
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
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

try:  # pragma: no cover - compatibility with lightweight SQLAlchemy stubs
    from sqlalchemy import Date
except ImportError:  # pragma: no cover
    Date = DateTime  # type: ignore[assignment]

try:  # pragma: no cover
    from sqlalchemy import UniqueConstraint
except ImportError:  # pragma: no cover
    class UniqueConstraint:  # type: ignore[too-many-ancestors]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.columns = args
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
    OPERATOR_ADMIN = "operator_admin"
    KITCHEN_MANAGER = "kitchen_manager"
    FOOD_BUSINESS_ADMIN = "food_business_admin"
    CITY_REVIEWER = "city_reviewer"
    SUPPORT_ANALYST = "support_analyst"
    REGULATORY_ADMIN = "regulatory_admin"


class SubscriptionStatus(str, enum.Enum):
    """Lifecycle states for platform subscriptions."""

    INACTIVE = "inactive"
    TRIAL = "trial"
    ACTIVE = "active"
    CANCELED = "canceled"


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


class RevenueType(str, enum.Enum):
    BOOKING = "booking"
    DELIVERY = "delivery"
    SHARED_SHELF = "shared_shelf"
class InventoryTransferStatus(str, enum.Enum):
    """Workflow states for peer-to-peer inventory transfers."""

    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class ComplianceDocumentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DocumentProcessingStatus(str, enum.Enum):
    """Lifecycle for uploaded compliance and onboarding documents."""

    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PermitStatus(str, enum.Enum):
    """States tracked for a business permit."""

    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class PaymentStatus(str, enum.Enum):
    """Possible payment lifecycle states for checkout flows."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"


class IntegrationStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


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


class DocumentUploadStatus(str, enum.Enum):
    STORED = "stored"
    PROCESSING = "processing"
    VERIFIED = "verified"
    REJECTED = "rejected"


class DocumentOCRStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CheckoutPaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    REQUIRES_ACTION = "requires_action"
    REFUND_REQUESTED = "refund_requested"
    REFUNDED = "refunded"
    FAILED = "failed"
class IdentityProviderType(str, enum.Enum):
    OIDC = "oidc"
    SAML = "saml"


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
    is_pilot_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pilot_county: Mapped[str | None] = mapped_column(String(255))


    pilot_zip_code: Mapped[str | None] = mapped_column(String(20))
    rbac_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.INACTIVE, nullable=False
    )
    trial_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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
    integrations: Mapped[List["Integration"]] = relationship(
        "Integration",
        back_populates="owner",
        cascade="all, delete-orphan",
        foreign_keys="Integration.user_id",
    )
    api_usage_events: Mapped[List["APIUsageEvent"]] = relationship(
        "APIUsageEvent", back_populates="user", cascade="all, delete-orphan"
    )
    identities: Mapped[List["UserIdentity"]] = relationship(
        "UserIdentity", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    identities: Mapped[List["UserIdentity"]] = relationship(
        "UserIdentity", back_populates="user", cascade="all, delete-orphan"
    )


class IdentityProvider(TimestampMixin, Base):
    __tablename__ = "identity_providers"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    provider_type: Mapped[IdentityProviderType] = mapped_column(
        Enum(IdentityProviderType), nullable=False
    )
    issuer: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_url: Mapped[str | None] = mapped_column(String(1024))
    client_id: Mapped[str | None] = mapped_column(String(255))
    client_secret: Mapped[str | None] = mapped_column(String(255))
    jwks_url: Mapped[str | None] = mapped_column(String(1024))
    sso_url: Mapped[str | None] = mapped_column(String(1024))
    acs_url: Mapped[str | None] = mapped_column(String(1024))
    certificate: Mapped[str | None] = mapped_column(Text)
    settings: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    identities: Mapped[List["UserIdentity"]] = relationship(
        "UserIdentity", back_populates="provider", cascade="all, delete-orphan"
    )


class UserIdentity(TimestampMixin, Base):
    __tablename__ = "user_identities"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("identity_providers.id", ondelete="CASCADE"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship("User", back_populates="identities")
    provider: Mapped[IdentityProvider] = relationship(
        "IdentityProvider", back_populates="identities"
    )

    __table_args__ = (
        UniqueConstraint("provider_id", "subject", name="uq_user_identity_subject"),
    )


class APIKey(TimestampMixin, Base):
    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    hashed_secret: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="api_keys")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_api_key_user_name"),
    )


class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    device_fingerprint: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")


class BusinessPermit(TimestampMixin, Base):
    __tablename__ = "business_permits"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    business_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("business_profiles.id"), nullable=False)
    permit_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    permit_type: Mapped[str] = mapped_column(String(120), nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(String(120))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[PermitStatus] = mapped_column(Enum(PermitStatus), default=PermitStatus.PENDING)
    permit_metadata: Mapped[dict | None] = mapped_column(JSON, default=dict)

    business: Mapped[BusinessProfile] = relationship("BusinessProfile", back_populates="permits")
    documents: Mapped[list["DocumentUpload"]] = relationship(
        "DocumentUpload", back_populates="permit", cascade="all, delete-orphan"
    )


class PaymentRecord(TimestampMixin, Base):
    __tablename__ = "payment_records"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    business_id: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("business_profiles.id"))
    booking_id: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("bookings.id"))
    provider_payment_id: Mapped[str | None] = mapped_column(String(255))
    provider: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    line_items: Mapped[list[dict] | None] = mapped_column(JSON, default=list)
    receipt_url: Mapped[str | None] = mapped_column(String(512))
    refunded_amount_cents: Mapped[int | None] = mapped_column(Integer)
    payment_metadata: Mapped[dict | None] = mapped_column(JSON, default=dict)

    business: Mapped[BusinessProfile | None] = relationship("BusinessProfile", back_populates="payments")
    booking: Mapped[Optional["Booking"]] = relationship("Booking")


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
    postal_code: Mapped[str | None] = mapped_column(String(20))
    county: Mapped[str | None] = mapped_column(String(120))
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
    delivery_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permit_types: Mapped[list[str] | None] = mapped_column(JSON, default=list)

    host: Mapped[User] = relationship("User", back_populates="kitchens")
    pos_integrations: Mapped[List["POSIntegration"]] = relationship(
        "POSIntegration", back_populates="kitchen", cascade="all, delete-orphan"
    )
    pos_transactions: Mapped[List["POSTransaction"]] = relationship(
        "POSTransaction", back_populates="kitchen", cascade="all, delete-orphan"
    )
    pos_orders: Mapped[List["POSOrder"]] = relationship(
        "POSOrder", back_populates="kitchen", cascade="all, delete-orphan"
    )

    integrations: Mapped[List["Integration"]] = relationship(
        "Integration",
        back_populates="kitchen",
        cascade="all, delete-orphan",
        foreign_keys="Integration.kitchen_id",
    )
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
    sanitation_logs: Mapped[List["SanitationLog"]] = relationship(
        "SanitationLog", back_populates="kitchen", cascade="all, delete-orphan"
    )
    recurring_templates: Mapped[List["RecurringBookingTemplate"]] = relationship(
        "RecurringBookingTemplate", back_populates="kitchen", cascade="all, delete-orphan"
    )


class POSIntegrationStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class POSIntegration(TimestampMixin, Base):
    __tablename__ = "pos_integrations"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    merchant_id: Mapped[str | None] = mapped_column(String(128))
    location_identifier: Mapped[str | None] = mapped_column(String(128))
    access_token: Mapped[str | None] = mapped_column(String(255))
    refresh_token: Mapped[str | None] = mapped_column(String(255))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[POSIntegrationStatus] = mapped_column(
        Enum(POSIntegrationStatus), default=POSIntegrationStatus.ACTIVE, nullable=False
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)

    kitchen: Mapped[Kitchen] = relationship("Kitchen", back_populates="pos_integrations")
    transactions: Mapped[List["POSTransaction"]] = relationship(
        "POSTransaction", back_populates="integration", cascade="all, delete-orphan"
    )
    orders: Mapped[List["POSOrder"]] = relationship(
        "POSOrder", back_populates="integration", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "kitchen_id", "provider", name="uq_pos_integration_kitchen_provider"
        ),
    )


class POSTransaction(TimestampMixin, Base):
    __tablename__ = "pos_transactions"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    integration_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("pos_integrations.id", ondelete="CASCADE"), nullable=False
    )
    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    location_id: Mapped[str | None] = mapped_column(String(120))
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    integration: Mapped[POSIntegration] = relationship(
        "POSIntegration", back_populates="transactions"
    )
    kitchen: Mapped[Kitchen] = relationship("Kitchen", back_populates="pos_transactions")

    __table_args__ = (
        UniqueConstraint(
            "provider", "external_id", name="uq_pos_transaction_provider_external"
        ),
        Index("ix_pos_transactions_kitchen_occurred_at", "kitchen_id", "occurred_at"),
    )


class POSOrder(TimestampMixin, Base):
    __tablename__ = "pos_orders"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    integration_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("pos_integrations.id", ondelete="SET NULL"), nullable=True
    )
    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    order_number: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    guest_count: Mapped[int | None] = mapped_column(Integer)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    kitchen: Mapped[Kitchen] = relationship("Kitchen", back_populates="pos_orders")
    integration: Mapped[POSIntegration] = relationship(
        "POSIntegration", back_populates="orders"
    )

    __table_args__ = (
        UniqueConstraint(
            "provider", "external_id", name="uq_pos_order_provider_external"
        ),
        Index("ix_pos_orders_kitchen_closed_at", "kitchen_id", "closed_at"),
    )


class Supplier(TimestampMixin, Base):
    """Vendors that provide inventory to Prep kitchens."""

    __tablename__ = "suppliers"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    phone_number: Mapped[str | None] = mapped_column(String(64))
    address: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    source: Mapped[str | None] = mapped_column(String(64))

    inventory_items: Mapped[List["InventoryItem"]] = relationship(
        "InventoryItem", back_populates="supplier"
    )


class InventoryItem(TimestampMixin, Base):
    """Aggregated inventory item tracked for a specific kitchen."""

    __tablename__ = "inventory_items"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False, index=True
    )
    host_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    supplier_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("suppliers.id", ondelete="SET NULL")
    )
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    source: Mapped[str] = mapped_column(String(64), default="manual", nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    par_level: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    total_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    oldest_expiry: Mapped[date | None] = mapped_column(Date)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shared_shelf_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    supplier: Mapped[Supplier | None] = relationship("Supplier", back_populates="inventory_items")
    kitchen: Mapped["Kitchen"] = relationship("Kitchen")
    host: Mapped[User] = relationship("User")
    lots: Mapped[List["InventoryLot"]] = relationship(
        "InventoryLot",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="InventoryLot.expiry_date",
    )
    transfers: Mapped[List["InventoryTransfer"]] = relationship(
        "InventoryTransfer",
        back_populates="item",
        cascade="all, delete-orphan",
        foreign_keys="InventoryTransfer.item_id",
    )


class InventoryLot(TimestampMixin, Base):
    """Quantity batch for an inventory item, used for FIFO depletion."""

    __tablename__ = "inventory_lots"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_reference: Mapped[str | None] = mapped_column(String(255))

    item: Mapped[InventoryItem] = relationship("InventoryItem", back_populates="lots")


class InventoryTransfer(TimestampMixin, Base):
    """Peer-to-peer ingredient sharing workflow between kitchens."""

    __tablename__ = "inventory_transfers"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False
    )
    from_kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    to_kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    requested_by_host_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    approved_by_host_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    approval_status: Mapped[InventoryTransferStatus] = mapped_column(
        Enum(InventoryTransferStatus),
        default=InventoryTransferStatus.PENDING,
        nullable=False,
        index=True,
    )
    expiry_date: Mapped[date | None] = mapped_column(Date)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    item: Mapped[InventoryItem] = relationship("InventoryItem", back_populates="transfers")
    from_kitchen: Mapped["Kitchen"] = relationship(
        "Kitchen", foreign_keys=[from_kitchen_id], lazy="joined"
    )
    to_kitchen: Mapped["Kitchen"] = relationship(
        "Kitchen", foreign_keys=[to_kitchen_id], lazy="joined"
    )
    requested_by_host: Mapped[User] = relationship(
        "User", foreign_keys=[requested_by_host_id], lazy="joined"
    )
    approved_by_host: Mapped[User | None] = relationship(
        "User", foreign_keys=[approved_by_host_id], lazy="joined"
    )


class Integration(TimestampMixin, Base):
    __tablename__ = "integrations"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kitchen_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="SET NULL"), nullable=True
    )
    service_type: Mapped[str] = mapped_column(String(120), nullable=False)
    vendor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    auth_method: Mapped[str] = mapped_column(String(50), nullable=False)
    sync_frequency: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(IntegrationStatus), default=IntegrationStatus.ACTIVE, nullable=False
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )

    owner: Mapped[User] = relationship(
        "User",
        back_populates="integrations",
        foreign_keys=[user_id],
    )
    kitchen: Mapped[Optional["Kitchen"]] = relationship(
        "Kitchen",
        back_populates="integrations",
        foreign_keys=[kitchen_id],
    )


class ChecklistTemplate(TimestampMixin, Base):
    """Versioned JSON schema used to power dynamic admin checklists."""

    __tablename__ = "checklist_templates"
    __table_args__ = ()

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
    sublease_contract: Mapped[SubleaseContract | None] = relationship(
        "SubleaseContract", back_populates="booking", uselist=False
    )
    ledger_entries: Mapped[List["LedgerEntry"]] = relationship(
        "LedgerEntry", back_populates="booking", cascade="all, delete-orphan"
    )
    tax_records: Mapped[List["TaxRecord"]] = relationship(
        "TaxRecord", back_populates="booking", cascade="all, delete-orphan"
    )


class StripeWebhookEvent(TimestampMixin, Base):
    __tablename__ = "stripe_webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class APIUsageEvent(TimestampMixin, Base):
    __tablename__ = "api_usage"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, default=dict
    )

    user: Mapped["User"] = relationship("User", back_populates="api_usage_events")


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


class SanitationLog(TimestampMixin, Base):
    """Documented sanitation checks for a kitchen."""

    __tablename__ = "sanitation_logs"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    kitchen_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    inspector_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32), default="passed", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    kitchen: Mapped["Kitchen"] = relationship("Kitchen", back_populates="sanitation_logs")


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


class LedgerEntry(TimestampMixin, Base):
    __tablename__ = "ledger_entries"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("bookings.id", ondelete="SET NULL"), index=True
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    debit_account: Mapped[str] = mapped_column(String(120), nullable=False)
    credit_account: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    revenue_type: Mapped[RevenueType | None] = mapped_column(
        Enum(RevenueType), nullable=True
    )
    expense_category: Mapped[str | None] = mapped_column(String(120))
    external_reference: Mapped[str | None] = mapped_column(String(120))
    details: Mapped[Dict[str, Any] | None] = mapped_column(JSON, default=dict)

    booking: Mapped[Optional["Booking"]] = relationship(
        "Booking", back_populates="ledger_entries"
    )

    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_reference",
            name="uq_ledger_entries_source_reference",
        ),
    )


class TaxRecord(TimestampMixin, Base):
    __tablename__ = "tax_records"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False
    )
    jurisdiction: Mapped[str] = mapped_column(String(120), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    details: Mapped[Dict[str, Any] | None] = mapped_column(JSON, default=dict)

    booking: Mapped["Booking"] = relationship("Booking", back_populates="tax_records")

    __table_args__ = (
        UniqueConstraint(
            "booking_id",
            "jurisdiction",
            name="uq_tax_records_booking_jurisdiction",
        ),
    )


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

    booking: Mapped[Optional["Booking"]] = relationship("Booking")
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
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, default=dict
    )

    delivery: Mapped[DeliveryOrder] = relationship("DeliveryOrder", back_populates="compliance_events")


class BusinessProfile(TimestampMixin, Base):
    """Represents a food business progressing through Prep onboarding."""

    __tablename__ = "business_profiles"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kitchen_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("kitchens.id", ondelete="SET NULL"), nullable=True
    )
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    doing_business_as: Mapped[str | None] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(2), default="US", nullable=False)
    region: Mapped[str | None] = mapped_column(String(64))
    readiness_stage: Mapped[str] = mapped_column(String(64), default="not_ready", nullable=False)
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    readiness_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)

    owner: Mapped[User] = relationship("User")
    kitchen: Mapped[Optional["Kitchen"]] = relationship("Kitchen")
    documents: Mapped[List["DocumentUpload"]] = relationship(
        "DocumentUpload", back_populates="business", cascade="all, delete-orphan"
    )
    permits: Mapped[List["Permit"]] = relationship(
        "Permit", back_populates="business", cascade="all, delete-orphan"
    )
    readiness_snapshots: Mapped[List["BusinessReadinessSnapshot"]] = relationship(
        "BusinessReadinessSnapshot", back_populates="business", cascade="all, delete-orphan"
    )
    payments: Mapped[List["CheckoutPayment"]] = relationship(
        "CheckoutPayment", back_populates="business"
    )


class DocumentUpload(TimestampMixin, Base):
    """Stores uploads used for compliance verification and OCR extraction."""

    __tablename__ = "document_uploads"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    business_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False
    )
    uploader_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    document_type: Mapped[str] = mapped_column(String(120), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120))
    storage_bucket: Mapped[str] = mapped_column(String(120), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[DocumentUploadStatus] = mapped_column(
        Enum(DocumentUploadStatus), default=DocumentUploadStatus.STORED, nullable=False
    )
    ocr_status: Mapped[DocumentOCRStatus] = mapped_column(
        Enum(DocumentOCRStatus), default=DocumentOCRStatus.PENDING, nullable=False
    )
    ocr_text: Mapped[str | None] = mapped_column(Text)
    ocr_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text)

    business: Mapped[BusinessProfile] = relationship("BusinessProfile", back_populates="documents")
    uploader: Mapped[User | None] = relationship("User")


class Permit(TimestampMixin, Base):
    """Permit or license tracked within the permit wallet."""

    __tablename__ = "permits"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    business_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    permit_type: Mapped[str] = mapped_column(String(120), nullable=False)
    permit_number: Mapped[str | None] = mapped_column(String(120), index=True)
    issuing_authority: Mapped[str | None] = mapped_column(String(255))
    jurisdiction: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[PermitStatus] = mapped_column(
        Enum(PermitStatus), default=PermitStatus.PENDING, nullable=False
    )
    issued_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    webhook_url: Mapped[str | None] = mapped_column(String(255))
    last_webhook_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    document_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("document_uploads.id", ondelete="SET NULL"), nullable=True
    )
    permit_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)

    business: Mapped[BusinessProfile] = relationship("BusinessProfile", back_populates="permits")
    document: Mapped[DocumentUpload | None] = relationship("DocumentUpload")


class BusinessReadinessSnapshot(TimestampMixin, Base):
    """Historical readiness snapshot for auditing gating decisions."""

    __tablename__ = "business_readiness_snapshots"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    business_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    checklist: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    gating_requirements: Mapped[list[str]] = mapped_column(JSON, default=list)
    outstanding_actions: Mapped[list[str]] = mapped_column(JSON, default=list)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    business: Mapped[BusinessProfile] = relationship(
        "BusinessProfile", back_populates="readiness_snapshots"
    )


class CheckoutPayment(TimestampMixin, Base):
    """Checkout session persisted for bookings and regulatory fees."""

    __tablename__ = "checkout_payments"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    business_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("business_profiles.id", ondelete="SET NULL"), nullable=True
    )
    booking_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[CheckoutPaymentStatus] = mapped_column(
        Enum(CheckoutPaymentStatus), default=CheckoutPaymentStatus.PENDING, nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    payment_provider: Mapped[str] = mapped_column(String(64), default="stripe", nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(255))
    receipt_url: Mapped[str | None] = mapped_column(String(255))
    payment_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    refund_reason: Mapped[str | None] = mapped_column(String(255))
    refund_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    business: Mapped[BusinessProfile | None] = relationship(
        "BusinessProfile", back_populates="payments"
    )
    booking: Mapped[Optional["Booking"]] = relationship("Booking")


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
    "SanitationLog",
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
    "RevenueType",
    "LedgerEntry",
    "TaxRecord",
    "RegDoc",
    "User",
    "UserRole",
    "UserIdentity",
    "IdentityProvider",
    "IdentityProviderType",
    "APIKey",
    "RefreshToken",
    "COIDocument",
    "DeliveryOrder",
    "DeliveryStatusEvent",
    "DeliveryComplianceEvent",
    "DeliveryStatus",
    "DeliveryProvider",
    "BusinessProfile",
    "DocumentUpload",
    "DocumentUploadStatus",
    "DocumentOCRStatus",
    "Permit",
    "PermitStatus",
    "BusinessReadinessSnapshot",
    "CheckoutPayment",
    "CheckoutPaymentStatus",
]
