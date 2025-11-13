from __future__ import annotations

import sys
import types
import uuid

import pytest
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import declarative_base, sessionmaker

from apps.city_regulatory_service.jurisdictions.common.fees import FeeItem, make_fee_schedule


@pytest.fixture()
def cli_environment(monkeypatch: pytest.MonkeyPatch):
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base = declarative_base()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    class CityJurisdiction(Base):
        __tablename__ = "city_jurisdictions"

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        city = Column(String, nullable=False)
        state = Column(String(2), nullable=False)
        data_source = Column(String)

    class CityAgency(Base):
        __tablename__ = "city_agencies"

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        jurisdiction_id = Column(String, ForeignKey("city_jurisdictions.id"), nullable=False)
        name = Column(String, nullable=False)
        agency_type = Column(String)

    class CityRequirement(Base):
        __tablename__ = "city_requirements"

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        jurisdiction_id = Column(String, ForeignKey("city_jurisdictions.id"), nullable=False)
        agency_id = Column(String, ForeignKey("city_agencies.id"))
        requirement_id = Column(String, nullable=False)
        requirement_label = Column(String, nullable=False)
        requirement_type = Column(String, nullable=False)
        applies_to = Column(JSON)
        required_documents = Column(JSON)
        submission_channel = Column(String)
        application_url = Column(String)
        inspection_required = Column(Integer)
        renewal_frequency = Column(String)
        renewal_cycle = Column(String)
        fee_amount = Column(String)
        fee_schedule = Column(String)
        fee_details = Column(JSON)
        enforcement_mechanism = Column(String)
        penalties = Column(JSON)
        rules = Column(JSON)
        source_url = Column(String)
        created_at = Column(DateTime)

    class CityFeeSchedule(Base):
        __tablename__ = "city_fee_schedules"

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        jurisdiction_id = Column(String, ForeignKey("city_jurisdictions.id"), nullable=False)
        jurisdiction_slug = Column(String, nullable=False)
        paperwork = Column(JSON)
        fees = Column(JSON)
        data_source = Column(String)
        created_at = Column(DateTime)
        updated_at = Column(DateTime)

    class CityRequirementLink(Base):  # minimal placeholder
        __tablename__ = "city_requirement_links"

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        city_requirement_id = Column(String, ForeignKey("city_requirements.id"))
        federal_scope_name = Column(String)

    class CityComplianceTemplate(Base):  # minimal placeholder
        __tablename__ = "city_compliance_templates"

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    class CityETLRun(Base):  # minimal placeholder
        __tablename__ = "city_etl_runs"

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        jurisdiction_id = Column(String, ForeignKey("city_jurisdictions.id"))

    Base.metadata.create_all(engine)

    db_module = types.ModuleType("prep.models.db")
    db_module.SessionLocal = SessionLocal
    db_module.init_db = lambda: None
    monkeypatch.setitem(sys.modules, "prep.models.db", db_module)

    reg_module = types.ModuleType("prep.regulatory.models")
    reg_module.CityJurisdiction = CityJurisdiction
    reg_module.CityAgency = CityAgency
    reg_module.CityRequirement = CityRequirement
    reg_module.CityRequirementLink = CityRequirementLink
    reg_module.CityComplianceTemplate = CityComplianceTemplate
    reg_module.CityETLRun = CityETLRun
    reg_module.CityFeeSchedule = CityFeeSchedule
    reg_module.__all__ = [
        "CityJurisdiction",
        "CityAgency",
        "CityRequirement",
        "CityRequirementLink",
        "CityComplianceTemplate",
        "CityETLRun",
        "CityFeeSchedule",
    ]
    monkeypatch.setitem(sys.modules, "prep.regulatory.models", reg_module)

    models_module = types.ModuleType("apps.city_regulatory_service.src.models")
    models_module.CityJurisdiction = CityJurisdiction
    models_module.CityAgency = CityAgency
    models_module.CityRequirement = CityRequirement
    models_module.CityRequirementLink = CityRequirementLink
    models_module.CityComplianceTemplate = CityComplianceTemplate
    models_module.CityETLRun = CityETLRun
    models_module.CityFeeSchedule = CityFeeSchedule
    models_module.__all__ = [
        "CityJurisdiction",
        "CityAgency",
        "CityRequirement",
        "CityRequirementLink",
        "CityComplianceTemplate",
        "CityETLRun",
        "CityFeeSchedule",
    ]
    monkeypatch.setitem(sys.modules, "apps.city_regulatory_service.src.models", models_module)

    etl_module = types.ModuleType("apps.city_regulatory_service.src.etl")
    etl_module.CITY_ADAPTERS = {}

    class _UnavailableOrchestrator:
        def __init__(self, session: Session):
            self.session = session

    etl_module.CityETLOrchestrator = _UnavailableOrchestrator
    monkeypatch.setitem(sys.modules, "apps.city_regulatory_service.src.etl", etl_module)

    import data.cli as cli

    yield cli, SessionLocal, CityJurisdiction, CityRequirement, CityFeeSchedule

    for name in [
        "prep.models.db",
        "prep.regulatory.models",
        "apps.city_regulatory_service.src.models",
        "apps.city_regulatory_service.src.etl",
    ]:
        monkeypatch.delitem(sys.modules, name, raising=False)


def test_cli_ingests_requirements_and_fees(
    cli_environment, monkeypatch: pytest.MonkeyPatch, tmp_path
):
    cli, SessionLocal, CityJurisdiction, CityRequirement, CityFeeSchedule = cli_environment

    module_name = "tests.fake_fee_ingestor"
    fee_module = types.SimpleNamespace(
        make_fee_schedule=lambda: make_fee_schedule(
            "testopolis",
            paperwork=["Form X"],
            fees=[
                FeeItem(name="Application", amount_cents=12300, kind="one_time"),
                FeeItem(name="Permit", amount_cents=45000, kind="recurring", cadence="annual"),
            ],
        )
    )
    monkeypatch.setitem(sys.modules, module_name, fee_module)

    spec = cli.CitySpec(
        slug="testopolis",
        display_name="Testopolis",
        state="TS",
        fee_module=module_name,
        supports_requirements=True,
    )

    class StubOrchestrator:
        def __init__(self, session: Session):
            self.session = session

        def run_etl_for_city(self, city: str) -> dict[str, object]:
            jurisdiction = cli._ensure_jurisdiction(
                self.session,
                cli.CitySpec(
                    slug=cli._slugify(city),
                    display_name=city,
                    state="TS",
                    supports_requirements=True,
                ),
            )
            agency = types.SimpleNamespace(id=str(uuid.uuid4()))
            self.session.add(
                CityRequirement(
                    jurisdiction_id=jurisdiction.id,
                    agency_id=agency.id,
                    requirement_id="TEST-REQ-001",
                    requirement_label="Test Health Permit",
                    requirement_type="health_permit",
                    applies_to=["test_kitchen"],
                    required_documents=["Form 123"],
                    submission_channel="online",
                    application_url="https://example.test/apply",
                    inspection_required=1,
                    renewal_frequency="annual",
                    renewal_cycle="annual",
                    fee_amount="100.00",
                    fee_schedule="test-schedule",
                    fee_details={"amount_cents": 10000},
                    enforcement_mechanism="inspection",
                    penalties={"late": "fine"},
                    rules={"note": "Be nice"},
                    source_url="https://example.test/source",
                )
            )
            return {"processed": 1, "inserted": 1, "updated": 0, "errors": []}

    results = cli.run_ingestion(
        ["Testopolis"],
        session_factory=SessionLocal,
        orchestrator_cls=StubOrchestrator,
        city_specs={spec.slug: spec},
    )

    session = SessionLocal()
    try:
        jurisdiction = session.execute(
            select(CityJurisdiction).where(CityJurisdiction.city == "Testopolis")
        ).scalar_one()
        requirement = session.execute(
            select(CityRequirement).where(CityRequirement.jurisdiction_id == jurisdiction.id)
        ).scalar_one()
        schedule = session.execute(
            select(CityFeeSchedule).where(CityFeeSchedule.jurisdiction_id == jurisdiction.id)
        ).scalar_one()
    finally:
        session.close()

    city_result = results["testopolis"]
    assert city_result["errors"] == []
    assert city_result["requirements"]["processed"] == 1
    assert city_result["fees"]["fee_count"] == 2
    assert requirement.requirement_label == "Test Health Permit"
    assert len(schedule.fees or []) == 2
    assert schedule.jurisdiction_slug == "testopolis"


def test_cli_reports_unknown_city(cli_environment):
    cli, SessionLocal, CityJurisdiction, *_ = cli_environment

    class StubOrchestrator:
        def __init__(self, session: Session):
            self.session = session

        def run_etl_for_city(self, city: str) -> dict[str, object]:  # pragma: no cover - defensive
            raise AssertionError("orchestrator should not be invoked for unknown cities")

    results = cli.run_ingestion(
        ["Unknown City"],
        session_factory=SessionLocal,
        orchestrator_cls=StubOrchestrator,
        city_specs={},
    )

    session = SessionLocal()
    try:
        jurisdictions = session.execute(select(CityJurisdiction)).all()
    finally:
        session.close()

    assert jurisdictions == []
    assert results == {
        "unknown_city": {
            "city": "unknown_city",
            "errors": ["unknown city 'unknown_city'"],
        }
    }
