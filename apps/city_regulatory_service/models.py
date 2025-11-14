"""
City Regulatory Service - Data Models

This module defines the data models for city-level compliance regulations,
including health permits, business licenses, insurance requirements, and
operational certifications across major US cities.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class RegulationType(str, Enum):
    """Types of city-level regulations"""

    HEALTH_PERMIT = "health_permit"
    BUSINESS_LICENSE = "business_license"
    FOOD_HANDLER_CERT = "food_handler_certification"
    FIRE_SAFETY = "fire_safety"
    BUILDING_PERMIT = "building_permit"
    ZONING = "zoning"
    PARKING = "parking"
    SIGNAGE = "signage"
    WASTE_MANAGEMENT = "waste_management"
    INSURANCE = "insurance"
    WORKERS_COMP = "workers_compensation"
    LIABILITY_INSURANCE = "liability_insurance"
    ALCOHOL_LICENSE = "alcohol_license"
    GREASE_TRAP = "grease_trap"
    FOOD_SAFETY_TRAINING = "food_safety_training"


class FacilityType(str, Enum):
    """Types of food service facilities"""

    COMMERCIAL_KITCHEN = "commercial_kitchen"
    GHOST_KITCHEN = "ghost_kitchen"
    RESTAURANT = "restaurant"
    CATERING = "catering"
    FOOD_TRUCK = "food_truck"
    BAKERY = "bakery"
    COMMISSARY = "commissary"
    PREP_KITCHEN = "prep_kitchen"


class ComplianceStatus(str, Enum):
    """Compliance status values"""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING_REVIEW = "pending_review"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    NOT_REQUIRED = "not_required"


# ============================================================================
# DATABASE MODELS
# ============================================================================


class CityJurisdiction(Base):
    """City jurisdiction information and regulatory contacts"""

    __tablename__ = "city_jurisdictions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    city_name = Column(String, nullable=False, index=True)
    state = Column(String(2), nullable=False, index=True)
    county = Column(String, nullable=True)
    country_code = Column(String(2), default="US", nullable=False)
    fips_code = Column(String, nullable=True)
    population = Column(Integer, nullable=True)

    # Primary regulatory contacts
    health_department_name = Column(String, nullable=True)
    health_department_url = Column(String, nullable=True)
    business_licensing_dept = Column(String, nullable=True)
    business_licensing_url = Column(String, nullable=True)
    fire_department_name = Column(String, nullable=True)
    fire_department_url = Column(String, nullable=True)

    # Contact information
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)

    # Metadata
    timezone = Column(String, default="America/New_York")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    data_source = Column(String, nullable=True)
    last_verified = Column(DateTime, nullable=True)


class CityRegulation(Base):
    """City-specific regulatory requirements"""

    __tablename__ = "city_regulations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    city_id = Column(String, ForeignKey("city_jurisdictions.id"), nullable=False, index=True)

    # Regulation identification
    regulation_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    local_code_reference = Column(String, nullable=True)

    # Federal/state linkage
    cfr_citation = Column(String, nullable=True)  # Links to federal scope
    state_code_reference = Column(String, nullable=True)  # Links to state requirement

    # Dates and validity
    effective_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    renewal_period_days = Column(Integer, nullable=True)

    # Enforcement
    enforcement_agency = Column(String, nullable=False)
    agency_contact = Column(String, nullable=True)
    agency_phone = Column(String, nullable=True)
    agency_url = Column(String, nullable=True)

    # Penalties
    penalty_for_violation = Column(Text, nullable=True)
    fine_amount_min = Column(Float, nullable=True)
    fine_amount_max = Column(Float, nullable=True)

    # Requirements detail
    requirements = Column(JSON, nullable=True)  # Structured requirement details
    application_process = Column(JSON, nullable=True)  # Steps to apply
    required_documents = Column(JSON, nullable=True)  # Document checklist
    fees = Column(JSON, nullable=True)  # Fee structure

    # Applicability
    applicable_facility_types = Column(JSON, nullable=False)  # List of FacilityType values
    employee_count_threshold = Column(Integer, nullable=True)
    revenue_threshold = Column(Float, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(String, default="medium")  # critical, high, medium, low

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    data_source = Column(String, nullable=True)
    last_verified = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)


class CityInsuranceRequirement(Base):
    """Insurance requirements by city and facility type"""

    __tablename__ = "city_insurance_requirements"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    city_id = Column(String, ForeignKey("city_jurisdictions.id"), nullable=False, index=True)

    # Insurance type
    insurance_type = Column(String, nullable=False)  # liability, workers_comp, property, etc.
    coverage_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Coverage requirements
    minimum_coverage_amount = Column(Float, nullable=False)  # In USD
    per_occurrence_limit = Column(Float, nullable=True)
    aggregate_limit = Column(Float, nullable=True)
    deductible_max = Column(Float, nullable=True)

    # Applicability
    applicable_facility_types = Column(JSON, nullable=False)
    employee_count_threshold = Column(Integer, nullable=True)

    # Regulatory reference
    local_ordinance = Column(String, nullable=True)
    state_requirement = Column(String, nullable=True)

    # Status
    is_mandatory = Column(Boolean, default=True)
    effective_date = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)


class CityPermitApplication(Base):
    """Permit application processes and timelines"""

    __tablename__ = "city_permit_applications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    city_id = Column(String, ForeignKey("city_jurisdictions.id"), nullable=False, index=True)
    regulation_id = Column(String, ForeignKey("city_regulations.id"), nullable=False)

    # Application details
    permit_name = Column(String, nullable=False)
    application_url = Column(String, nullable=True)
    submission_method = Column(JSON, nullable=True)  # online, mail, in_person

    # Timeline
    processing_time_days = Column(Integer, nullable=True)
    processing_time_notes = Column(Text, nullable=True)

    # Costs
    application_fee = Column(Float, nullable=True)
    renewal_fee = Column(Float, nullable=True)
    late_fee = Column(Float, nullable=True)

    # Requirements
    prerequisite_permits = Column(JSON, nullable=True)  # IDs of other required permits
    required_inspections = Column(JSON, nullable=True)

    # Contact
    responsible_dept = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FacilityComplianceStatus(Base):
    """Compliance status tracking for facilities in each city"""

    __tablename__ = "facility_compliance_status"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    facility_id = Column(String, nullable=False, index=True)  # Kitchen ID from main system
    city_id = Column(String, ForeignKey("city_jurisdictions.id"), nullable=False, index=True)
    regulation_id = Column(String, ForeignKey("city_regulations.id"), nullable=False, index=True)

    # Status
    compliance_status = Column(String, nullable=False)  # From ComplianceStatus enum
    last_check_date = Column(DateTime, nullable=False)
    next_check_due = Column(DateTime, nullable=True)

    # Details
    permit_number = Column(String, nullable=True)
    issue_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)

    # Violations
    has_violations = Column(Boolean, default=False)
    violation_count = Column(Integer, default=0)
    violation_details = Column(JSON, nullable=True)

    # Inspector information
    last_inspector_name = Column(String, nullable=True)
    last_inspection_score = Column(Integer, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)


# ============================================================================
# PYDANTIC MODELS (API Schemas)
# ============================================================================


class CityJurisdictionSchema(BaseModel):
    """API schema for city jurisdiction"""

    id: str
    city_name: str
    state: str
    county: str | None = None
    country_code: str = "US"
    fips_code: str | None = None
    population: int | None = None

    health_department_name: str | None = None
    health_department_url: str | None = None
    business_licensing_dept: str | None = None
    business_licensing_url: str | None = None
    fire_department_name: str | None = None
    fire_department_url: str | None = None

    phone: str | None = None
    email: str | None = None
    address: str | None = None
    timezone: str = "America/New_York"

    created_at: datetime
    updated_at: datetime
    last_verified: datetime | None = None

    class Config:
        from_attributes = True


class CityRegulationSchema(BaseModel):
    """API schema for city regulation"""

    id: str
    city_id: str
    regulation_type: str
    title: str
    description: str | None = None
    local_code_reference: str | None = None
    cfr_citation: str | None = None
    state_code_reference: str | None = None

    effective_date: datetime | None = None
    expiration_date: datetime | None = None
    renewal_period_days: int | None = None

    enforcement_agency: str
    agency_contact: str | None = None
    agency_phone: str | None = None
    agency_url: str | None = None

    penalty_for_violation: str | None = None
    fine_amount_min: float | None = None
    fine_amount_max: float | None = None

    requirements: dict[str, Any] | None = None
    application_process: dict[str, Any] | None = None
    required_documents: list[str] | None = None
    fees: dict[str, float] | None = None

    applicable_facility_types: list[str]
    employee_count_threshold: int | None = None
    revenue_threshold: float | None = None

    is_active: bool = True
    priority: str = "medium"

    created_at: datetime
    updated_at: datetime
    last_verified: datetime | None = None
    notes: str | None = None

    class Config:
        from_attributes = True


class CityInsuranceRequirementSchema(BaseModel):
    """API schema for insurance requirements"""

    id: str
    city_id: str
    insurance_type: str
    coverage_name: str
    description: str | None = None

    minimum_coverage_amount: float
    per_occurrence_limit: float | None = None
    aggregate_limit: float | None = None
    deductible_max: float | None = None

    applicable_facility_types: list[str]
    employee_count_threshold: int | None = None

    local_ordinance: str | None = None
    state_requirement: str | None = None

    is_mandatory: bool = True
    effective_date: datetime | None = None

    created_at: datetime
    updated_at: datetime
    notes: str | None = None

    class Config:
        from_attributes = True


class ComplianceCheckRequest(BaseModel):
    """Request to check compliance for a facility"""

    facility_id: str
    city_name: str
    state: str
    facility_type: FacilityType
    employee_count: int | None = None
    annual_revenue: float | None = None
    current_permits: list[dict[str, Any]] | None = None
    current_insurance: list[dict[str, Any]] | None = None


class ComplianceCheckResponse(BaseModel):
    """Response from compliance check"""

    facility_id: str
    city_name: str
    state: str
    overall_compliant: bool
    compliance_score: float = Field(ge=0.0, le=100.0)

    required_regulations: list[CityRegulationSchema]
    compliant_regulations: list[str]  # Regulation IDs
    non_compliant_regulations: list[str]  # Regulation IDs
    missing_requirements: list[dict[str, Any]]

    insurance_compliant: bool
    insurance_gaps: list[str] | None = None

    recommended_actions: list[dict[str, Any]]
    estimated_cost_to_comply: float | None = None
    estimated_time_to_comply_days: int | None = None

    check_timestamp: datetime
    next_review_date: datetime | None = None


class RegulationSummary(BaseModel):
    """Summary of regulations for a city"""

    city_name: str
    state: str
    total_regulations: int
    by_type: dict[str, int]
    by_priority: dict[str, int]
    total_facility_types: int
    last_updated: datetime


class DataIngestionRequest(BaseModel):
    """Request to ingest new regulatory data"""

    city_name: str
    state: str
    regulations: list[dict[str, Any]]
    insurance_requirements: list[dict[str, Any]] | None = None
    jurisdiction_info: dict[str, Any] | None = None
    data_source: str
    verification_date: datetime = Field(default_factory=datetime.utcnow)


class DataIngestionResponse(BaseModel):
    """Response from data ingestion"""

    success: bool
    city_id: str
    regulations_imported: int
    insurance_requirements_imported: int
    errors: list[str] | None = None
    warnings: list[str] | None = None
    import_timestamp: datetime = Field(default_factory=datetime.utcnow)
