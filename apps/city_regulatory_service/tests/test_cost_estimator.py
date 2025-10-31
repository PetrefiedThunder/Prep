from __future__ import annotations

import sys
import types
from typing import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import JSON, Column, ForeignKey, String, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

# The regulatory models package pulls in aiohttp at import time.  The estimator
# does not use aiohttp directly, so we stub it out for isolated unit tests.
sys.modules.setdefault("aiohttp", types.SimpleNamespace())

# Provide a lightweight stand-in for ``prep.regulatory.models`` so that we can
# exercise the estimator without importing the full production ORM (which has
# heavy dependencies and circular imports in this environment).
if "prep.regulatory.models" not in sys.modules:
    Base = declarative_base()

    class CityJurisdiction(Base):
        __tablename__ = "city_jurisdictions"

        id = Column(String, primary_key=True, default=lambda: str(uuid4()))
        city = Column(String, nullable=False)
        state = Column(String, nullable=False)

    class CityAgency(Base):
        __tablename__ = "city_agencies"

        id = Column(String, primary_key=True, default=lambda: str(uuid4()))
        jurisdiction_id = Column(String, ForeignKey("city_jurisdictions.id"), nullable=False)
        name = Column(String, nullable=False)
        agency_type = Column(String, nullable=True)

        jurisdiction = relationship("CityJurisdiction", backref="agencies")

    class CityRequirement(Base):
        __tablename__ = "city_requirements"

        id = Column(String, primary_key=True, default=lambda: str(uuid4()))
        jurisdiction_id = Column(String, ForeignKey("city_jurisdictions.id"), nullable=False)
        agency_id = Column(String, ForeignKey("city_agencies.id"))
        requirement_id = Column(String, nullable=False)
        requirement_label = Column(String, nullable=False)
        requirement_type = Column(String, nullable=False)
        applies_to = Column(JSON, default=list)
        required_documents = Column(JSON, default=list)
        submission_channel = Column(String, nullable=True)
        fee_amount = Column(String, nullable=True)
        fee_schedule = Column(String, nullable=True)
        fee_details = Column(JSON, nullable=True)
        source_url = Column(String, nullable=True)

        agency = relationship("CityAgency", backref="requirements")

    fake_models = types.ModuleType("prep.regulatory.models")
    fake_models.Base = Base
    fake_models.CityJurisdiction = CityJurisdiction
    fake_models.CityAgency = CityAgency
    fake_models.CityRequirement = CityRequirement
    fake_models.CityRequirementLink = type("CityRequirementLink", (), {})
    fake_models.CityComplianceTemplate = type("CityComplianceTemplate", (), {})
    fake_models.CityETLRun = type("CityETLRun", (), {})

    fake_regulatory = types.ModuleType("prep.regulatory")
    fake_regulatory.__path__ = []  # mark as package
    fake_regulatory.models = fake_models

    sys.modules["prep.regulatory"] = fake_regulatory
    sys.modules["prep.regulatory.models"] = fake_models

    # Expose Base for importers that expect ``prep.models.Base`` style access.
    sys.modules.setdefault("prep.models", types.SimpleNamespace(Base=Base))

from apps.city_regulatory_service.src.estimators import estimate_costs, load_bundle
from apps.city_regulatory_service.src.models import RequirementsBundle
from prep.regulatory.models import Base, CityAgency, CityJurisdiction, CityRequirement


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()
    try:
        yield session
    finally:
        session.close()


def _seed_requirement_data(session: Session) -> CityJurisdiction:
    jurisdiction = CityJurisdiction(city="Sample City", state="SC")
    session.add(jurisdiction)
    session.flush()

    agency = CityAgency(
        jurisdiction_id=jurisdiction.id,
        name="Sample Agency",
        agency_type="licensing",
    )
    session.add(agency)
    session.flush()

    requirement_one = CityRequirement(
        jurisdiction_id=jurisdiction.id,
        agency_id=agency.id,
        requirement_id="req-one",
        requirement_label="Business License",
        requirement_type="business_license",
        applies_to=["restaurant"],
        required_documents=["application"],
        submission_channel="online",
        fee_details={
            "components": [
                {"label": "Application", "amount": 125.50, "frequency": "one-time"}
            ]
        },
        source_url="https://example.com/business",
    )
    session.add(requirement_one)

    requirement_two = CityRequirement(
        jurisdiction_id=jurisdiction.id,
        agency_id=agency.id,
        requirement_id="req-two",
        requirement_label="Health Permit",
        requirement_type="restaurant_license",
        applies_to=["restaurant"],
        required_documents=["plan"],
        submission_channel="in_person",
        fee_details={
            "components": [
                {
                    "label": "Annual Permit",
                    "amount": 200,
                    "frequency": "annual",
                    "notes": "Recurring",
                }
            ]
        },
        source_url="https://example.com/health",
    )
    session.add(requirement_two)

    requirement_three = CityRequirement(
        jurisdiction_id=jurisdiction.id,
        agency_id=agency.id,
        requirement_id="req-three",
        requirement_label="Inspection Fee",
        requirement_type="inspection",
        applies_to=["restaurant"],
        required_documents=[],
        submission_channel="online",
        fee_amount="$30",
        fee_schedule="Per inspection",
        source_url="https://example.com/inspection",
    )
    session.add(requirement_three)

    session.commit()
    return jurisdiction


def test_load_bundle_and_estimate_costs(db_session: Session) -> None:
    jurisdiction = _seed_requirement_data(db_session)

    bundle = load_bundle(db_session, jurisdiction=jurisdiction.city)
    assert isinstance(bundle, RequirementsBundle)
    assert bundle.jurisdiction_name == "Sample City"
    assert bundle.state == "SC"
    assert len(bundle.requirements) == 3

    requirements_by_id = {req.requirement_id: req for req in bundle.requirements}

    business_costs = requirements_by_id["req-one"].fee_schedule
    assert business_costs.total_one_time_cents == 12550
    assert business_costs.total_recurring_annualized_cents == 0

    permit_costs = requirements_by_id["req-two"].fee_schedule
    assert permit_costs.total_one_time_cents == 0
    assert permit_costs.total_recurring_annualized_cents == 20000

    inspection_costs = requirements_by_id["req-three"].fee_schedule
    assert inspection_costs.total_one_time_cents == 3000
    assert inspection_costs.has_incremental

    combined_schedule = bundle.fee_schedule
    assert combined_schedule.total_one_time_cents == 12550 + 3000
    assert combined_schedule.total_recurring_annualized_cents == 20000

    summary = estimate_costs(bundle)
    assert summary["jurisdiction"]["name"] == "Sample City"
    assert summary["summary"]["one_time_cents"] == 15550
    assert summary["summary"]["recurring_annualized_cents"] == 20000
    assert summary["summary"]["has_incremental_fees"] is True
    assert summary["summary"]["requirement_count"] == 3

    items = summary["requirements"]
    labels = {entry["requirement_id"] for entry in items}
    assert labels == {"req-one", "req-two", "req-three"}
    inspection_entry = next(entry for entry in items if entry["requirement_id"] == "req-three")
    assert inspection_entry["has_incremental_fees"] is True
    assert inspection_entry["one_time_cents"] == 3000


def test_load_bundle_missing_jurisdiction_raises(db_session: Session) -> None:
    with pytest.raises(LookupError):
        load_bundle(db_session, jurisdiction="Not a Real City")
