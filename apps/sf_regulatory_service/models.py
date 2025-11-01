"""ORM models for the San Francisco regulatory service."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import Mapped
from sqlalchemy.types import JSON, TypeDecorator

from .database import Base

COMPLIANCE_STATUSES = ("compliant", "flagged", "blocked")
TAX_CLASSIFICATIONS = ("lease_sublease", "service_provider")
FACILITY_TYPES = (
    "cooking_kitchen",
    "commissary_non_cooking",
    "mobile_food_commissary",
)
BOOKING_STATUSES = ("passed", "flagged", "blocked")


class JsonTextArray(TypeDecorator):
    """Compatibility wrapper that stores arrays as JSON when needed."""

    cache_ok = True
    impl = JSON

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):  # type: ignore[override]
        if value is None:
            return [] if dialect.name == "postgresql" else json.dumps([])
        if dialect.name == "postgresql":
            return list(value)
        return json.dumps(list(value))

    def process_result_value(self, value, dialect):  # type: ignore[override]
        if value is None:
            return []
        if dialect.name == "postgresql":
            return list(value)
        if isinstance(value, str):
            return json.loads(value)
        return list(value)


class MutableJsonList(Mutable, list):
    """Mutable wrapper that triggers SQLAlchemy change tracking."""

    @classmethod
    def coerce(cls, key, value):  # type: ignore[override]
        if isinstance(value, cls):
            return value
        if isinstance(value, list):
            return cls(value)
        return super().coerce(key, value)

    def append(self, value):  # type: ignore[override]
        list.append(self, value)
        self.changed()

    def extend(self, iterable):  # type: ignore[override]
        list.extend(self, iterable)
        self.changed()

    def remove(self, value):  # type: ignore[override]
        list.remove(self, value)
        self.changed()


MutableJsonList.associate_with(JsonTextArray)


class SFHostProfile(Base):
    """San Francisco host compliance profile."""

    __tablename__ = "sf_host_profiles"

    host_kitchen_id: Mapped[str] = Column(String, primary_key=True)
    business_registration_certificate: Mapped[str] = Column(String, nullable=False)
    business_registration_expires: Mapped[date] = Column(Date, nullable=False)
    health_permit_number: Mapped[str] = Column(String, nullable=False)
    health_permit_expires: Mapped[date] = Column(Date, nullable=False)
    facility_type: Mapped[str] = Column(
        Enum(*FACILITY_TYPES, name="sf_facility_type"),
        nullable=False,
    )
    zoning_use_district: Mapped[str] = Column(String, nullable=False)
    fire_suppression_certificate: Mapped[Optional[str]] = Column(String)
    fire_last_inspection: Mapped[Optional[date]] = Column(Date)
    grease_trap_certificate: Mapped[Optional[str]] = Column(String)
    grease_last_service: Mapped[Optional[date]] = Column(Date)
    tax_classification: Mapped[str] = Column(
        Enum(*TAX_CLASSIFICATIONS, name="sf_tax_classification"),
        nullable=False,
    )
    lease_gross_receipts_ytd: Mapped[float] = Column(Numeric(14, 2), server_default=text("0"))
    compliance_status: Mapped[str] = Column(
        Enum(*COMPLIANCE_STATUSES, name="sf_compliance_status"),
        nullable=False,
        server_default="flagged",
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class SFZoningVerification(Base):
    """Zoning verification attempts."""

    __tablename__ = "sf_zoning_verifications"

    id: Mapped[str] = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    host_kitchen_id: Mapped[Optional[str]] = Column(String)
    address: Mapped[str] = Column(Text, nullable=False)
    zoning_use_district: Mapped[str] = Column(String, nullable=False)
    kitchen_use_allowed: Mapped[bool] = Column(Boolean, nullable=False)
    verification_date: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    manual_review_required: Mapped[bool] = Column(Boolean, nullable=False, default=False)


class SFBookingCompliance(Base):
    """Booking time compliance decisions."""

    __tablename__ = "sf_booking_compliance"

    booking_id: Mapped[str] = Column(String, primary_key=True)
    prebooking_status: Mapped[str] = Column(
        Enum(*BOOKING_STATUSES, name="sf_booking_status"),
        nullable=False,
    )
    issues: Mapped[List[str]] = Column(JsonTextArray, nullable=False, default=list)
    evaluated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class SFTaxLedger(Base):
    """Tax ledger entries for San Francisco bookings."""

    __tablename__ = "sf_tax_ledger"

    id: Mapped[str] = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id: Mapped[Optional[str]] = Column(String)
    tax_jurisdiction: Mapped[str] = Column(String, nullable=False)
    tax_basis: Mapped[float] = Column(Numeric(14, 2), nullable=False)
    tax_rate: Mapped[float] = Column(Numeric(7, 4), nullable=False)
    tax_amount: Mapped[float] = Column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class SFTaxReport(Base):
    """Quarterly tax report metadata."""

    __tablename__ = "sf_tax_reports"

    id: Mapped[str] = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    period_start: Mapped[datetime] = Column(Date, nullable=False)
    period_end: Mapped[datetime] = Column(Date, nullable=False)
    total_tax_collected: Mapped[float] = Column(Numeric(14, 2), nullable=False)
    total_booking_amount: Mapped[float] = Column(Numeric(14, 2), nullable=False)
    file_status: Mapped[str] = Column(
        Enum("not_prepared", "prepared", "remitted", name="sf_tax_file_status"),
        nullable=False,
        server_default="not_prepared",
    )
    generated_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))


class CityEtlRun(Base):
    """Nightly ETL observability record."""

    __tablename__ = "city_etl_runs"

    id: Mapped[str] = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    city: Mapped[str] = Column(String, nullable=False)
    run_date: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    records_extracted: Mapped[int] = Column(Integer, nullable=False)
    records_changed: Mapped[int] = Column(Integer, nullable=False)
    status: Mapped[str] = Column(
        Enum("success", "partial", "failure", name="city_etl_status"),
        nullable=False,
    )
    diff_summary: Mapped[Optional[str]] = Column(Text)
