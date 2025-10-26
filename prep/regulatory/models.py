"""Database models supporting regulatory compliance features."""

from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.dialects.postgresql import ARRAY

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
    applicable_to = Column(ARRAY(String))
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
    required_policies = Column(ARRAY(String))
    special_requirements = Column(Text)
    notes = Column(Text)
    source_url = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)


__all__ = ["RegulationSource", "Regulation", "InsuranceRequirement"]
