"""Tests for the requirements bundle loader and cost estimator."""

from __future__ import annotations

from datetime import datetime
import sys
import types
from typing import Iterator

if "aiohttp" not in sys.modules:
    aiohttp_stub = types.ModuleType("aiohttp")

    class _StubTimeout:  # pragma: no cover - minimal placeholder
        def __init__(self, *_, **__) -> None:  # noqa: D401 - simple stub
            """Placeholder that mimics :class:`aiohttp.ClientTimeout`."""

    class _StubSession:  # pragma: no cover - minimal placeholder
        def __init__(self, *_, **__) -> None:
            raise RuntimeError("aiohttp is required for HTTP operations")

    aiohttp_stub.ClientTimeout = _StubTimeout
    aiohttp_stub.ClientSession = _StubSession
    sys.modules["aiohttp"] = aiohttp_stub

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import apps.city_regulatory_service.src.estimator as estimator
from apps.city_regulatory_service.src.models.requirements import (
    FeeItem,
    FeeSchedule,
    Jurisdiction,
    RequirementRecord,
    RequirementsBundle,
)

CostEstimate = estimator.CostEstimate
estimate_costs = estimator.estimate_costs
load_bundle = estimator.load_bundle
CityJurisdiction = estimator.CityJurisdiction
CityAgency = estimator.CityAgency
CityRequirement = estimator.CityRequirement


class TestEstimateCosts:
    """Unit tests for the in-memory cost estimator."""

    def test_estimate_costs_breakdown(self) -> None:
        """Estimator should aggregate one-time, recurring, and incremental fees."""

        fee_items = (
            FeeItem(
                name="Plan Review",
                amount_cents=12500,
                kind="one_time",
                requirement_id="req-plan",
            ),
            FeeItem(
                name="Annual Permit",
                amount_cents=4500,
                kind="recurring",
                cadence="annual",
                requirement_id="req-permit",
            ),
            FeeItem(
                name="Reinspection",
                amount_cents=1200,
                kind="recurring",
                cadence="monthly",
                incremental=True,
                unit="per_inspection",
                requirement_id="req-inspection",
            ),
            FeeItem(
                name="Misc Fee",
                amount_cents=2500,
                kind="one_time",
            ),
        )

        schedule = FeeSchedule(
            jurisdiction="Testville, TS",
            paperwork=("Application",),
            fees=fee_items,
        )

        requirements = (
            RequirementRecord(
                id="req-plan",
                label="Plan Review",
                requirement_type="building",
                applies_to=("restaurant",),
                required_documents=("Application",),
                submission_channel="online",
                application_url="https://example.com/plan",
                inspection_required=False,
                renewal_frequency=None,
                fee_schedule="one-time",
                fee_amount_cents=12500,
                agency_name="Health Dept",
                agency_type="health",
                source_url="https://example.com/plan",
            ),
            RequirementRecord(
                id="req-permit",
                label="Health Permit",
                requirement_type="health",
                applies_to=("restaurant",),
                required_documents=("Permit Form",),
                submission_channel="online",
                application_url="https://example.com/permit",
                inspection_required=True,
                renewal_frequency="annual",
                fee_schedule="annual",
                fee_amount_cents=4500,
                agency_name="Health Dept",
                agency_type="health",
                source_url="https://example.com/permit",
            ),
            RequirementRecord(
                id="req-inspection",
                label="Inspection",
                requirement_type="inspection",
                applies_to=("restaurant",),
                required_documents=("Inspection Log",),
                submission_channel="in_person",
                application_url=None,
                inspection_required=True,
                renewal_frequency="monthly",
                fee_schedule="per inspection",
                fee_amount_cents=1200,
                agency_name="Health Dept",
                agency_type="health",
                source_url="https://example.com/inspection",
            ),
        )

        jurisdiction = Jurisdiction(id="test", city="Testville", state="TS")
        bundle = RequirementsBundle(
            jurisdiction=jurisdiction,
            requirements=requirements,
            fee_schedule=schedule,
        )

        estimate = estimate_costs(bundle)
        assert isinstance(estimate, CostEstimate)
        assert estimate.total_one_time_cents == 15000  # 12500 + 2500
        assert estimate.total_recurring_annualized_cents == 4500
        assert estimate.incremental_fee_count == 1
        assert estimate.per_requirement["req-plan"].one_time_cents == 12500
        assert estimate.per_requirement["req-permit"].recurring_annualized_cents == 4500
        assert estimate.per_requirement["req-inspection"].incremental_fee_count == 1
        assert "__unassigned__" in estimate.per_requirement
        assert estimate.per_requirement["__unassigned__"].one_time_cents == 2500


class TestLoadBundle:
    """Integration-style tests for the bundle loader."""

    @pytest.fixture()
    def session(self) -> Iterator[Session]:
        engine = create_engine("sqlite:///:memory:", future=True)
        CityJurisdiction.__table__.metadata.create_all(engine)
        factory = sessionmaker(bind=engine, future=True)
        with factory() as session:
            yield session

    def test_load_bundle_constructs_fee_schedule(self, session: Session) -> None:
        jurisdiction = CityJurisdiction(city="Testville", state="TS", county="Test")
        session.add(jurisdiction)
        session.flush()

        agency = CityAgency(
            jurisdiction_id=jurisdiction.id,
            name="Health Department",
            agency_type="health",
        )
        session.add(agency)
        session.flush()

        requirement_one = CityRequirement(
            jurisdiction_id=jurisdiction.id,
            agency_id=agency.id,
            requirement_id="req-1",
            requirement_label="Health Permit",
            requirement_type="health_permit",
            applies_to=["restaurant"],
            required_documents=["Health Application"],
            submission_channel="online",
            application_url="https://example.com/health",
            inspection_required=True,
            renewal_frequency="annual",
            fee_amount="450.00",
            fee_schedule="Annual renewal",
            fee_details={},
            enforcement_mechanism=None,
            penalties=None,
            rules={},
            source_url="https://example.com/health",
            last_updated=datetime.utcnow(),
        )

        requirement_two = CityRequirement(
            jurisdiction_id=jurisdiction.id,
            agency_id=agency.id,
            requirement_id="req-2",
            requirement_label="Plan Review",
            requirement_type="building",
            applies_to=["restaurant"],
            required_documents=["Plan Set"],
            submission_channel="online",
            application_url="https://example.com/plan",
            inspection_required=False,
            renewal_frequency=None,
            fee_amount="125.50",
            fee_schedule="one-time",
            fee_details={},
            enforcement_mechanism=None,
            penalties=None,
            rules={},
            source_url="https://example.com/plan",
            last_updated=datetime.utcnow(),
        )

        session.add_all([requirement_one, requirement_two])
        session.commit()

        bundle = load_bundle(session, city="Testville", state="TS")

        assert bundle.jurisdiction.city == "Testville"
        assert len(bundle.requirements) == 2
        assert {item.requirement_id for item in bundle.fee_schedule.fees} == {"req-1", "req-2"}
        assert set(bundle.fee_schedule.paperwork) == {"Health Application", "Plan Set"}

        estimate = estimate_costs(bundle)
        assert estimate.total_one_time_cents == 12550
        assert estimate.total_recurring_annualized_cents == 45000
        assert estimate.incremental_fee_count == 0

