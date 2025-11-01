"""Database models supporting regulatory compliance features."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.mutable import MutableDict, MutableList

from prep.models import Base
from prep.models.guid import GUID


class RegulationSource(Base):
    """Source metadata for a collection of regulations."""

    __tablename__ = "regulation_sources"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    country_code = Column(String(2), nullable=False, default="US")
    state = Column(String(2), nullable=False)
    state_province = Column(String(100))
    city = Column(String(100))
    source_url = Column(Text, nullable=False)
    source_type = Column(String(50))
    last_scraped = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Regulation(Base):
    """Individual regulation entries scraped from government sources."""

    __tablename__ = "regulations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    source_id = Column(GUID(), ForeignKey("regulation_sources.id"))
    regulation_type = Column(String(100), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text)
    requirements = Column(JSON)
    applicable_to = Column(MutableList.as_mutable(JSON))
    effective_date = Column(DateTime)
    expiration_date = Column(DateTime)
    jurisdiction = Column(String(100))
    country_code = Column(String(2), nullable=False, default="US")
    state_province = Column(String(100))
    citation = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InsuranceRequirement(Base):
    """Insurance coverage expectations by jurisdiction."""

    __tablename__ = "insurance_requirements"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    country_code = Column(String(2), nullable=False, default="US")
    state = Column(String(2), nullable=False)
    state_province = Column(String(100))
    city = Column(String(100))
    minimum_coverage = Column(JSON)
    required_policies = Column(MutableList.as_mutable(JSON))
    special_requirements = Column(Text)
    notes = Column(Text)
    source_url = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)


class RegDoc(Base):
    """Normalized regulatory documents with content hashing."""

    __tablename__ = "regdocs"
    __table_args__ = (
        UniqueConstraint("sha256_hash", name="uq_regdocs_sha256_hash"),
        Index("ix_regdocs_sha256_hash", "sha256_hash"),
        Index("ix_regdocs_jurisdiction", "jurisdiction"),
        Index("ix_regdocs_state_doc_type", "state", "doc_type"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    sha256_hash = Column(String(64), nullable=False)
    jurisdiction = Column(String(120))
    country_code = Column(String(2), nullable=False, default="US")
    state = Column(String(2))
    state_province = Column(String(120))
    city = Column(String(120))
    doc_type = Column(String(100))
    title = Column(String(255))
    summary = Column(Text)
    source_url = Column(Text)
    raw_payload = Column(MutableDict.as_mutable(JSON), nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CityJurisdiction(Base):
    """City jurisdiction registry with metadata."""

    __tablename__ = "city_jurisdictions"
    __table_args__ = (
        UniqueConstraint("city", "state", name="uq_city_state"),
        Index("ix_city_jurisdictions_state", "state"),
        Index("ix_city_jurisdictions_fips", "fips_code"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    county = Column(String(100))
    fips_code = Column(String(10))
    population = Column(Integer)
    food_code_adoption_year = Column(Integer)
    food_code_version = Column(String(50))
    portal_url = Column(Text)
    business_license_url = Column(Text)
    health_department_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CityAgency(Base):
    """Government agencies that enforce city regulations."""

    __tablename__ = "city_agencies"
    __table_args__ = (Index("ix_city_agencies_jurisdiction", "jurisdiction_id"),)

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    jurisdiction_id = Column(GUID(), ForeignKey("city_jurisdictions.id"), nullable=False)
    name = Column(String(255), nullable=False)
    agency_type = Column(String(100))
    contact_email = Column(String(255))
    contact_phone = Column(String(50))
    portal_link = Column(Text)
    application_portal = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CityRequirement(Base):
    """Normalized city-level regulatory requirements."""

    __tablename__ = "city_requirements"
    __table_args__ = (
        Index("ix_city_requirements_jurisdiction", "jurisdiction_id"),
        Index("ix_city_requirements_type", "requirement_type"),
        Index("ix_city_requirements_applies_to", "applies_to"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    jurisdiction_id = Column(GUID(), ForeignKey("city_jurisdictions.id"), nullable=False)
    agency_id = Column(GUID(), ForeignKey("city_agencies.id"))
    requirement_id = Column(String(255), nullable=False)
    requirement_label = Column(String(255), nullable=False)
    requirement_type = Column(String(100), nullable=False)
    applies_to = Column(MutableList.as_mutable(JSON))
    required_documents = Column(MutableList.as_mutable(JSON))
    submission_channel = Column(String(100))
    application_url = Column(Text)
    inspection_required = Column(Boolean, default=False)
    renewal_frequency = Column(String(50))
    renewal_cycle = Column(String(100))
    fee_amount = Column(String(50))
    fee_schedule = Column(String(255))
    fee_details = Column(MutableDict.as_mutable(JSON))
    enforcement_mechanism = Column(Text)
    penalties = Column(MutableDict.as_mutable(JSON))
    rules = Column(MutableDict.as_mutable(JSON))
    source_url = Column(Text, nullable=False)
    official_code_section = Column(String(255))
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CityFeeSchedule(Base):
    """Persisted fee schedules by city jurisdiction."""

    __tablename__ = "city_fee_schedules"
    __table_args__ = (
        UniqueConstraint("jurisdiction_id", name="uq_city_fee_schedule_jurisdiction"),
        Index("ix_city_fee_schedules_jurisdiction", "jurisdiction_id"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    jurisdiction_id = Column(GUID(), ForeignKey("city_jurisdictions.id"), nullable=False)
    jurisdiction_slug = Column(String(120), nullable=False)
    paperwork = Column(MutableList.as_mutable(JSON), default=list)
    fees = Column(MutableList.as_mutable(JSON), default=list)
    data_source = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CityRequirementLink(Base):
    """Links city requirements to federal requirements."""

    __tablename__ = "city_requirement_links"
    __table_args__ = (
        Index("ix_city_requirement_links_city", "city_requirement_id"),
        Index("ix_city_requirement_links_federal", "federal_scope_name"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    city_requirement_id = Column(GUID(), ForeignKey("city_requirements.id"), nullable=False)
    federal_scope_name = Column(String(255))


class PolicyDecision(Base):
    """Persisted evaluation results from policy engine executions."""

    __tablename__ = "policy_decisions"
    __table_args__ = (
        Index("ix_policy_decisions_request_hash", "request_hash"),
        Index("ix_policy_decisions_region_jurisdiction", "region", "jurisdiction"),
        Index("ix_policy_decisions_decision_created", "decision", "created_at"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    request_hash = Column(String(64), nullable=False)
    region = Column(String(64), nullable=False)
    jurisdiction = Column(String(120), nullable=False)
    package_path = Column(String(255), nullable=False)
    decision = Column(String(32), nullable=False)
    rationale = Column(String(1024))
    error = Column(String(1024))
    duration_ms = Column(Integer, nullable=False, default=0)
    input_payload = Column(MutableDict.as_mutable(JSON), nullable=False, default=dict)
    result_payload = Column(MutableDict.as_mutable(JSON))
    trace_id = Column(String(64))
    request_id = Column(String(64))
    triggered_by = Column(String(64))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    relationship_type = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class CityComplianceTemplate(Base):
    """Pre-built compliance checklists for city onboarding."""

    __tablename__ = "city_compliance_templates"
    __table_args__ = (Index("ix_city_compliance_templates_jurisdiction", "jurisdiction_id"),)

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    jurisdiction_id = Column(GUID(), ForeignKey("city_jurisdictions.id"), nullable=False)
    business_type = Column(String(100), nullable=False)
    template_name = Column(String(255), nullable=False)
    checklist_items = Column(MutableList.as_mutable(JSON))
    estimated_timeline_days = Column(Integer)
    estimated_total_cost = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CityETLRun(Base):
    """Tracks city regulatory data ingestion runs."""

    __tablename__ = "city_etl_runs"
    __table_args__ = (
        Index("ix_city_etl_runs_jurisdiction", "jurisdiction_id"),
        Index("ix_city_etl_runs_status", "status"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    jurisdiction_id = Column(GUID(), ForeignKey("city_jurisdictions.id"), nullable=False)
    run_started_at = Column(DateTime, nullable=False)
    run_completed_at = Column(DateTime)
    status = Column(String(50), nullable=False)
    requirements_processed = Column(Integer, default=0)
    requirements_inserted = Column(Integer, default=0)
    requirements_updated = Column(Integer, default=0)
    errors = Column(MutableList.as_mutable(JSON))
    metadata = Column(MutableDict.as_mutable(JSON))


__all__ = [
    "RegulationSource",
    "Regulation",
    "InsuranceRequirement",
    "RegDoc",
    "CityJurisdiction",
    "CityAgency",
    "CityRequirement",
    "CityFeeSchedule",
    "CityRequirementLink",
    "CityComplianceTemplate",
    "CityETLRun",
]
