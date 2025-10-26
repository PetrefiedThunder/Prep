"""SQLAlchemy ORM models for the Prep platform."""

from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID as PGUUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    """Registered Prep platform user."""

    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Kitchen(Base):
    """Kitchen listing managed by a host."""

    __tablename__ = "kitchens"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    host_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    address = Column(Text, nullable=False)
    cert_level = Column(String)
    photos = Column(ARRAY(String))
    pricing = Column(JSON)
    description = Column(Text)
    equipment = Column(ARRAY(String))
    state = Column(String(2))
    city = Column(String(100))
    compliance_status = Column(String(20), default="unknown")
    risk_score = Column(Integer, default=0)
    last_compliance_check = Column(DateTime)
    health_permit_number = Column(String(100))
    last_inspection_date = Column(DateTime)
    insurance_info = Column(JSON)
    zoning_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Booking(Base):
    """Booking created by a renter for a kitchen."""

    __tablename__ = "bookings"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    kitchen_id = Column(PGUUID(as_uuid=True), ForeignKey("kitchens.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String, default="pending")
    total_amount = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Review(Base):
    """Kitchen review authored by a renter."""

    __tablename__ = "reviews"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    kitchen_id = Column(PGUUID(as_uuid=True), ForeignKey("kitchens.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class ComplianceDocument(Base):
    """Compliance documentation linked to a kitchen."""

    __tablename__ = "compliance_documents"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id = Column(PGUUID(as_uuid=True), ForeignKey("kitchens.id"), nullable=False)
    document_type = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    status = Column(String, default="pending")
    verified_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    verified_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


__all__ = [
    "Base",
    "User",
    "Kitchen",
    "Booking",
    "Review",
    "ComplianceDocument",
]
