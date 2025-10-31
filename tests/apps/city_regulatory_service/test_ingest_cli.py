from __future__ import annotations

from typing import Any

import sys
import types
import uuid
from datetime import datetime

import pytest
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator

# ---------------------------------------------------------------------------
# Minimal prep.models stubs for isolated testing
# ---------------------------------------------------------------------------

Base = declarative_base()


class _GUID(TypeDecorator):
    impl = String
    cache_ok = True


_prep_models = types.ModuleType("prep.models")
_prep_models.Base = Base
sys.modules["prep.models"] = _prep_models

_prep_models_guid = types.ModuleType("prep.models.guid")
_prep_models_guid.GUID = _GUID
sys.modules["prep.models.guid"] = _prep_models_guid

_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_SessionLocal = sessionmaker(bind=_engine, future=True)


def _init_db() -> None:
    Base.metadata.create_all(bind=_engine)


_prep_models_db = types.ModuleType("prep.models.db")
_prep_models_db.SessionLocal = _SessionLocal
_prep_models_db.engine = _engine
_prep_models_db.get_db_url = lambda: "sqlite+pysqlite:///:memory:"
_prep_models_db.init_db = _init_db
sys.modules["prep.models.db"] = _prep_models_db

# Ensure prep package exposes the stub for attribute access
import prep  # noqa: E402

prep.models = _prep_models  # type: ignore[attr-defined]


class CityJurisdiction(Base):
    __tablename__ = "city_jurisdictions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    county = Column(String(100))


class CityAgency(Base):
    __tablename__ = "city_agencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    jurisdiction_id = Column(String(36), ForeignKey("city_jurisdictions.id"), nullable=False)
    name = Column(String(255), nullable=False)
    agency_type = Column(String(100))
    portal_link = Column(Text)


class CityRequirement(Base):
    __tablename__ = "city_requirements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    jurisdiction_id = Column(String(36), ForeignKey("city_jurisdictions.id"), nullable=False)
    agency_id = Column(String(36), ForeignKey("city_agencies.id"))
    requirement_id = Column(String(255), nullable=False)
    requirement_label = Column(String(255), nullable=False)
    requirement_type = Column(String(100), nullable=False)
    applies_to = Column(JSON)
    required_documents = Column(JSON)
    submission_channel = Column(String(100))
    application_url = Column(Text)
    inspection_required = Column(Boolean, default=False)
    renewal_frequency = Column(String(50))
    fee_amount = Column(String(50))
    fee_schedule = Column(String(255))
    rules = Column(JSON)
    source_url = Column(Text, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class CityRequirementLink(Base):
    __tablename__ = "city_requirement_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city_requirement_id = Column(String(36), ForeignKey("city_requirements.id"))
    federal_scope_name = Column(String(255))


class CityComplianceTemplate(Base):
    __tablename__ = "city_compliance_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(100))
    name = Column(String(255))
    description = Column(Text)
    url = Column(Text)


class CityETLRun(Base):
    __tablename__ = "city_etl_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jurisdiction_id = Column(String(36), ForeignKey("city_jurisdictions.id"), nullable=False)
    run_started_at = Column(DateTime, default=datetime.utcnow)
    run_completed_at = Column(DateTime)
    status = Column(String(50), nullable=False)
    requirements_processed = Column(Integer, default=0)
    requirements_inserted = Column(Integer, default=0)
    requirements_updated = Column(Integer, default=0)
    errors = Column(JSON)


_prep_reg_models = types.ModuleType("prep.regulatory.models")
_prep_reg_models.Base = Base
_prep_reg_models.CityJurisdiction = CityJurisdiction
_prep_reg_models.CityAgency = CityAgency
_prep_reg_models.CityRequirement = CityRequirement
_prep_reg_models.CityRequirementLink = CityRequirementLink
_prep_reg_models.CityComplianceTemplate = CityComplianceTemplate
_prep_reg_models.CityETLRun = CityETLRun
_prep_reg_models.__all__ = [
    "CityJurisdiction",
    "CityAgency",
    "CityRequirement",
    "CityRequirementLink",
    "CityComplianceTemplate",
    "CityETLRun",
]
sys.modules["prep.regulatory.models"] = _prep_reg_models

from prep.regulatory.models import CityJurisdiction, CityRequirement  # noqa: E402

from apps.city_regulatory_service.src.etl import cli as ingest_cli  # noqa: E402
from apps.city_regulatory_service.src.etl import orchestrator as orchestrator_module  # noqa: E402


class _StubAdapter:
    CITY_NAME = "Test City"
    STATE = "TC"

    @classmethod
    def get_all_requirements(cls) -> list[dict[str, Any]]:
        return [
            {
                "requirement_id": "tc_health_permit",
                "jurisdiction": cls.CITY_NAME,
                "requirement_type": "health_permit",
                "agency": "Test Health Department",
                "agency_type": "health",
                "requirement_label": "Shared Kitchen Permit",
                "applies_to": ["shared kitchen"],
                "required_documents": ["Floor plan"],
                "renewal_cycle": "annual",
                "submission_channel": "online",
                "inspection_required": True,
                "application_url": "https://example.com/apply",
                "fee_structure": {"amount": 123.45, "frequency": "annual"},
                "rules": {"notes": "Initial inspection required"},
                "official_url": "https://example.com/permit",
            }
        ]


@pytest.fixture()
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)


def test_cli_persists_requirements_and_fees(monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]) -> None:
    stub_adapters = {"Test City": _StubAdapter}

    monkeypatch.setattr(ingest_cli, "CITY_ADAPTERS", stub_adapters)
    monkeypatch.setattr(orchestrator_module, "CITY_ADAPTERS", stub_adapters)

    results = ingest_cli.run_ingestion(
        cities=["Test City"],
        session_factory=session_factory,
        adapters=stub_adapters,
    )

    assert results["Test City"]["status"] == "completed"
    assert results["Test City"]["inserted"] == 1
    assert results["Test City"]["updated"] == 0

    with session_factory() as session:
        requirements = session.execute(select(CityRequirement)).scalars().all()
        assert len(requirements) == 1
        requirement = requirements[0]
        assert requirement.requirement_label == "Shared Kitchen Permit"
        # SQLAlchemy coerces floats to strings for this column; normalise for comparison.
        assert float(requirement.fee_amount) == pytest.approx(123.45)
        assert requirement.fee_schedule == "annual"

        jurisdictions = session.execute(select(CityJurisdiction)).scalars().all()
        assert len(jurisdictions) == 1
        assert jurisdictions[0].city == "Test City"


def test_cli_skips_unknown_city(monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]) -> None:
    stub_adapters = {"Test City": _StubAdapter}

    monkeypatch.setattr(ingest_cli, "CITY_ADAPTERS", stub_adapters)
    monkeypatch.setattr(orchestrator_module, "CITY_ADAPTERS", stub_adapters)

    results = ingest_cli.run_ingestion(
        cities=["Atlantis"],
        session_factory=session_factory,
        adapters=stub_adapters,
    )

    assert results["Atlantis"]["status"] == "skipped"
    assert results["Atlantis"]["reason"] == "unsupported_city"
