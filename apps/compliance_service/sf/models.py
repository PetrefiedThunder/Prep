"""Pydantic models for the San Francisco compliance module."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, constr


class FacilityType(str, Enum):
    """Supported facility types for San Francisco hosts."""

    COOKING_KITCHEN = "cooking_kitchen"
    COMMISSARY_NON_COOKING = "commissary_non_cooking"
    MOBILE_FOOD_COMMISSARY = "mobile_food_commissary"


class TaxClassification(str, Enum):
    """Supported tax classifications for SF bookings."""

    SERVICE_PROVIDER = "service_provider"
    LEASE_SUBLEASE = "lease_sublease"


class HostKitchenRecord(BaseModel):
    """Source-of-truth record tracked for SF host onboarding."""

    id: UUID
    sf_business_registration_certificate: constr(strip_whitespace=True, min_length=1)
    registration_expiry_date: date
    sf_health_permit_number: str | None = None
    health_permit_expiry_date: date | None = None
    facility_type: FacilityType
    zoning_use_district: constr(strip_whitespace=True, min_length=1)
    grease_trap_certificate: str | None = None
    grease_service_last_date: date | None = None
    fire_suppression_certificate: str | None = None
    suppression_inspection_last_date: date | None = None
    tax_classification: TaxClassification
    lease_gross_receipts_ytd: float | None = Field(default=None, ge=0)


class HostComplianceFieldStatus(BaseModel):
    """Detailed per-field compliance information."""

    field: str
    status: Literal["ok", "missing", "expired", "invalid"]
    message: str | None = None


class HostComplianceStatus(BaseModel):
    """Aggregate compliance output for a host."""

    host_id: UUID
    overall_status: Literal["compliant", "needs_attention", "blocked"]
    checklist: list[HostComplianceFieldStatus]
    outstanding_issues: list[str]


class ZoningVerificationRecord(BaseModel):
    """Result of geocoding + zoning verification."""

    hostKitchenId: UUID
    address: str
    zoning_use_district: str
    kitchen_use_allowed: bool
    verification_date: datetime
    manual_review_required: bool = False
    message: str | None = None


class TaxCalculationRequest(BaseModel):
    """Request payload for SF tax calculation."""

    booking_amount: float = Field(gt=0)
    tax_classification: TaxClassification
    hostKitchenId: UUID | None = None


class TaxBreakdown(BaseModel):
    """Computed SF tax breakdown."""

    tax_rate: float
    tax_amount: float
    exemptions_applied: Sequence[str] = Field(default_factory=tuple)
    jurisdiction: str = "San Francisco"
    notes: str | None = None


class TaxReportRecord(BaseModel):
    """Quarterly aggregation of SF tax data."""

    period_start: date
    period_end: date
    jurisdiction: str
    total_tax_collected: float
    total_booking_amount: float
    file_status: Literal["not_prepared", "prepared", "remitted"] = "not_prepared"


class HealthPermitRecord(BaseModel):
    """Health permit metadata for SF hosts."""

    permit_number: str
    hostKitchenId: UUID
    facility_type: FacilityType
    issue_date: date
    expiry_date: date
    status: Literal["valid", "expired", "suspended", "revoked"]
    verification_method: Literal["api_lookup", "manual_upload"]
    verification_date: datetime


class FireComplianceRecord(BaseModel):
    """Fire suppression compliance tracking."""

    hostKitchenId: UUID
    suppression_certificate: str
    last_inspection_date: date
    suppression_system_type: str
    status: Literal["compliant", "non_compliant", "pending"]
    verification_date: datetime


class WasteComplianceRecord(BaseModel):
    """Grease trap and waste management compliance."""

    hostKitchenId: UUID
    grease_trap_certificate: str
    last_service_date: date
    next_due_date: date
    status: Literal["compliant", "due_soon", "overdue"]
    verification_date: datetime


class BookingFlowRecord(BaseModel):
    """Compliance snapshot produced during booking validation."""

    bookingId: UUID
    hostKitchenId: UUID
    renterId: UUID
    prebooking_compliance_status: Literal["passed", "flagged", "blocked"]
    compliance_issues: list[str]


class CityETLRunRecord(BaseModel):
    """Metadata about San Francisco regulatory ETL jobs."""

    city: str = "San Francisco"
    run_date: datetime
    records_extracted: int
    records_changed: int
    status: Literal["success", "partial", "failure"]
    diff_summary: str


class BookingValidationRequest(BaseModel):
    """Internal payload for booking compliance validation."""

    bookingId: UUID
    hostKitchenId: UUID
    renterId: UUID


class MetricsSnapshot(BaseModel):
    """Aggregated metrics emitted by the compliance service."""

    sf_permit_validations_total: int
    sf_zoning_checks_failures: int
    sf_tax_collections_total: float
    sf_compliance_blocked_bookings: int
    sf_api_response_time_seconds: float | None = None
