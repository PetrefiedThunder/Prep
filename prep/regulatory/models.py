"""Database models supporting regulatory compliance features."""

from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.ext.mutable import MutableList

from prep.models import Base
from prep.models.guid import GUID


class RegulationSource(Base):
    """Source metadata for a collection of regulations."""

    __tablename__ = "regulation_sources"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    state = Column(String(2), nullable=False)
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
    citation = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InsuranceRequirement(Base):
    """Insurance coverage expectations by jurisdiction."""

    __tablename__ = "insurance_requirements"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    state = Column(String(2), nullable=False)
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

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    sha256_hash = Column(String(64), nullable=False, unique=True, index=True)
    jurisdiction = Column(String(120))
    state = Column(String(2))
    city = Column(String(120))
    doc_type = Column(String(100))
    title = Column(String(255))
    summary = Column(Text)
    source_url = Column(Text)
    raw_payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


__all__ = ["RegulationSource", "Regulation", "InsuranceRequirement", "RegDoc"]
    """Normalized regulatory document content."""

    __tablename__ = "reg_docs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    jurisdiction = Column(String(100), nullable=False)
    code_section = Column(String(100), nullable=False)
    requirement_text = Column(Text, nullable=False)
    effective_date = Column(DateTime)
    citation_url = Column(Text)
    sha256_hash = Column(String(64), nullable=False, unique=True)


__all__ = [
    "RegulationSource",
    "Regulation",
    "InsuranceRequirement",
    "RegDoc",
]
