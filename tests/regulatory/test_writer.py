from __future__ import annotations

import sys
import types
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


class _StubBase(DeclarativeBase):
    pass


_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)

_stub_models = types.ModuleType("prep.models")
_stub_models.Base = _StubBase
_stub_models.__path__ = [str(Path(__file__).resolve().parents[2] / "prep" / "models")]
sys.modules["prep.models"] = _stub_models

_stub_db = types.ModuleType("prep.models.db")
_stub_db.SessionLocal = SessionLocal
_stub_db.engine = _engine
_stub_db.get_db_url = lambda: "sqlite+pysqlite:///:memory:"
sys.modules["prep.models.db"] = _stub_db

_stub_aiohttp = types.ModuleType("aiohttp")
_stub_aiohttp.ClientSession = object
sys.modules.setdefault("aiohttp", _stub_aiohttp)

_stub_regulatory = types.ModuleType("prep.regulatory")
_stub_regulatory.__path__ = [str(Path(__file__).resolve().parents[2] / "prep" / "regulatory")]
sys.modules["prep.regulatory"] = _stub_regulatory

import importlib.util

models_spec = importlib.util.spec_from_file_location(
    "prep.regulatory.models",
    Path(__file__).resolve().parents[2] / "prep" / "regulatory" / "models.py",
)
models_module = importlib.util.module_from_spec(models_spec)
sys.modules["prep.regulatory.models"] = models_module
models_spec.loader.exec_module(models_module)

writer_spec = importlib.util.spec_from_file_location(
    "prep.regulatory.writer",
    Path(__file__).resolve().parents[2] / "prep" / "regulatory" / "writer.py",
)
writer_module = importlib.util.module_from_spec(writer_spec)
sys.modules["prep.regulatory.writer"] = writer_module
writer_spec.loader.exec_module(writer_module)

from prep.regulatory.models import FeeSchedule, RegRequirement
from prep.regulatory.writer import write_fee_schedule, write_reg_requirements


@pytest.fixture(autouse=True)
def reset_database() -> None:
    _StubBase.metadata.drop_all(bind=_engine)
    _StubBase.metadata.create_all(bind=_engine)
    # ensure no sessions leak between tests
    session = SessionLocal()
    session.close()


def test_write_fee_schedule_inserts_and_updates() -> None:
    initial = {
        "jurisdiction": "san_francisco",
        "version": "2024",
        "paperwork": ["Form A"],
        "fees": [
            {"name": "Permit", "amount_cents": 10000, "kind": "one_time"},
            {
                "name": "Inspection",
                "amount_cents": 5000,
                "kind": "recurring",
                "cadence": "annual",
            },
        ],
        "notes": "Initial schedule",
    }

    write_fee_schedule(initial)

    session = SessionLocal()
    try:
        record = session.execute(select(FeeSchedule)).scalar_one()
    finally:
        session.close()

    assert record.jurisdiction == "san_francisco"
    assert record.totals["one_time_cents"] == 10000
    assert record.totals["recurring_annualized_cents"] == 5000
    assert record.totals["incremental_fee_count"] == 0
    assert record.paperwork == ["Form A"]

    updated = {
        "jurisdiction": "san_francisco",
        "version": "2024",
        "paperwork": ["Form A", "Form B"],
        "fees": [
            {"name": "Permit", "amount_cents": 12000, "kind": "one_time"},
            {
                "name": "Inspection",
                "amount_cents": 5000,
                "kind": "recurring",
                "cadence": "annual",
            },
            {
                "name": "Reinspection",
                "amount_cents": 1500,
                "kind": "incremental",
            },
        ],
        "notes": "Updated schedule",
    }

    write_fee_schedule(updated)

    session = SessionLocal()
    try:
        updated_record = session.execute(select(FeeSchedule)).scalar_one()
    finally:
        session.close()

    assert updated_record.paperwork == ["Form A", "Form B"]
    assert updated_record.totals["one_time_cents"] == 12000
    assert updated_record.totals["incremental_fee_count"] == 1


def test_write_reg_requirements_inserts_and_updates() -> None:
    write_fee_schedule(
        {
            "jurisdiction": "san_francisco",
            "version": "2024",
            "paperwork": ["Form A"],
            "fees": [
                {"name": "Permit", "amount_cents": 12000, "kind": "one_time"},
            ],
        }
    )

    session = SessionLocal()
    try:
        schedule = session.execute(select(FeeSchedule)).scalar_one()
    finally:
        session.close()

    requirement_a = {
        "requirement_id": "req-001",
        "jurisdiction": "san_francisco",
        "state": "ca",
        "requirement_type": "health_permit",
        "requirement_label": "Health Permit",
        "governing_agency": "SF Department of Public Health",
        "agency_type": "health",
        "submission_channel": "online",
        "application_url": "https://example.com/apply",
        "inspection_required": True,
        "renewal_frequency": "annual",
        "applies_to": ["restaurant", "ghost_kitchen"],
        "required_documents": ["Application", "Plan"],
        "rules": {"inspection": "required"},
        "source_url": "https://example.com/rule",
        "last_updated": datetime(2024, 1, 1).isoformat(),
        "fee_amount": 180.0,
        "fee_schedule_reference": "2024",
        "fee_schedule_id": str(schedule.id),
    }

    requirement_b = {
        "requirement_id": "req-002",
        "jurisdiction": "san_francisco",
        "requirement_type": "business_license",
        "requirement_label": "Business License",
        "governing_agency": "SF Office of Small Business",
        "submission_channel": "in_person",
        "applies_to": ["restaurant"],
        "required_documents": ["Application"],
        "rules": {},
        "fee_amount_cents": 4500,
    }

    result = write_reg_requirements([requirement_a, requirement_b])

    assert result == {"inserted": 2, "updated": 0}

    session = SessionLocal()
    try:
        stored = (
            session.execute(select(RegRequirement).order_by(RegRequirement.external_id))
            .scalars()
            .all()
        )
    finally:
        session.close()

    assert len(stored) == 2

    first = stored[0]
    assert first.external_id == "req-001"
    assert first.fee_schedule_id == schedule.id
    assert first.fee_amount_cents == 18000
    assert first.inspection_required is True
    assert sorted(first.required_documents) == ["Application", "Plan"]

    update_payload = dict(requirement_a)
    update_payload["required_documents"] = ["Application", "Plan", "Fire Certificate"]
    update_payload["fee_amount"] = 200.0
    update_payload["inspection_required"] = False

    result_update = write_reg_requirements([update_payload])

    assert result_update == {"inserted": 0, "updated": 1}

    session = SessionLocal()
    try:
        updated_record = session.execute(
            select(RegRequirement).where(RegRequirement.external_id == "req-001")
        ).scalar_one()
    finally:
        session.close()

    assert updated_record.fee_amount_cents == 20000
    assert sorted(updated_record.required_documents) == [
        "Application",
        "Fire Certificate",
        "Plan",
    ]
    assert updated_record.inspection_required is False
