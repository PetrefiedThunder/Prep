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
    String,
    Text,
    UniqueConstraint,
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


__all__ = [
    "RegulationSource",
    "Regulation",
    "InsuranceRequirement",
    "RegDoc",
]
__all__ = ["RegulationSource", "Regulation", "InsuranceRequirement", "RegDoc"]
