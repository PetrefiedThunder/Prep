"""SQLAlchemy ORM models for Vendor Verification."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from prep.models.guid import GUID
from prep.models.orm import Base


class Tenant(Base):
    """Tenant/customer using the vendor verification service."""

    __tablename__ = "tenants"

    id = Column(GUID(), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    api_key_hash = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    vendors = relationship("Vendor", back_populates="tenant", cascade="all, delete-orphan")
    verification_runs = relationship(
        "VerificationRun", back_populates="tenant", cascade="all, delete-orphan"
    )
    audit_events = relationship("AuditEvent", back_populates="tenant", cascade="all, delete-orphan")


class Vendor(Base):
    """Vendor being onboarded and verified."""

    __tablename__ = "vendors"
    __table_args__ = (UniqueConstraint("tenant_id", "external_id", name="uq_vendor_tenant_external"),)

    id = Column(GUID(), primary_key=True, default=uuid4)
    tenant_id = Column(GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id = Column(String(255), nullable=False)
    legal_name = Column(String(255), nullable=False)
    doing_business_as = Column(String(255), nullable=True)
    status = Column(
        String(50),
        nullable=False,
        default="onboarding",
        index=True,
    )

    # Location stored as JSON
    primary_location = Column(JSONB, nullable=False)

    # Contact info stored as JSON
    contact = Column(JSONB, nullable=True)

    # Tax ID last 4 digits
    tax_id_last4 = Column(String(4), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="vendors")
    documents = relationship("VendorDocument", back_populates="vendor", cascade="all, delete-orphan")
    verification_runs = relationship(
        "VerificationRun", back_populates="vendor", cascade="all, delete-orphan"
    )


class VendorDocument(Base):
    """Document uploaded for a vendor."""

    __tablename__ = "vendor_documents"

    id = Column(GUID(), primary_key=True, default=uuid4)
    vendor_id = Column(GUID(), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)

    # Jurisdiction stored as JSON (country, state, city)
    jurisdiction = Column(JSONB, nullable=False)

    expires_on = Column(DateTime(timezone=True), nullable=True)
    storage_key = Column(String(512), nullable=False)
    file_name = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    vendor = relationship("Vendor", back_populates="documents")


class VerificationRun(Base):
    """A verification run for a vendor."""

    __tablename__ = "verification_runs"

    id = Column(GUID(), primary_key=True, default=uuid4)
    tenant_id = Column(GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(GUID(), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(
        String(50),
        nullable=False,
        default="pending_documents",
        index=True,
    )

    # Jurisdiction stored as JSON
    jurisdiction = Column(JSONB, nullable=False)

    kitchen_id = Column(String(255), nullable=True)
    initiated_by = Column(String(255), nullable=True)
    initiated_from = Column(String(50), nullable=False, default="api")

    # Ruleset and engine metadata
    ruleset_name = Column(String(255), nullable=False)
    regulation_version = Column(String(100), nullable=False)
    engine_version = Column(String(100), nullable=False)

    # Decision and recommendation stored as JSONB
    decision_snapshot = Column(JSONB, nullable=True)

    # Hash of inputs/documents for idempotency
    inputs_hash = Column(String(64), nullable=True, index=True)

    # Idempotency key
    idempotency_key = Column(String(255), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    evaluated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="verification_runs")
    vendor = relationship("Vendor", back_populates="verification_runs")


class AuditEvent(Base):
    """Audit log for vendor verification events."""

    __tablename__ = "audit_events"

    id = Column(GUID(), primary_key=True, default=uuid4)
    tenant_id = Column(GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    actor_type = Column(String(50), nullable=False)  # api, ui
    actor_id = Column(String(255), nullable=True)

    event_type = Column(String(100), nullable=False, index=True)  # vendor_created, verification_completed, etc.
    entity_type = Column(String(50), nullable=False)  # vendor, verification, document
    entity_id = Column(String(255), nullable=False)

    # Event payload as JSONB
    payload = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="audit_events")
