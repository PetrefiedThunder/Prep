from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from sqlalchemy import delete, select

import prep.regulatory.models  # noqa: F401 - ensure models registered
from prep.models.db import Base, SessionLocal, engine
from prep.regulatory.models import FeeSchedule, RegRequirement
from prep.regulatory.writer import write_fee_schedule, write_reg_requirements


@pytest.fixture(autouse=True)
def _ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)
    yield
    with SessionLocal() as session:
        session.execute(delete(RegRequirement))
        session.execute(delete(FeeSchedule))
        session.commit()


def _sample_fee_items() -> list[dict[str, Any]]:
    return [
        {"name": "Health Permit", "amount_cents": 75000, "kind": "recurring", "cadence": "annual"},
        {"name": "Plan Review", "amount_cents": 25000},
    ]


def test_write_fee_schedule_uses_shared_session() -> None:
    schedule = write_fee_schedule(
        jurisdiction="san_francisco",
        paperwork=["Application", "Floor Plan"],
        fees=_sample_fee_items(),
        notes="Initial schedule",
        metadata={"source": "fixture"},
        effective_date=datetime.utcnow(),
    )

    with SessionLocal() as session:
        persisted = session.execute(select(FeeSchedule)).scalar_one()
        assert persisted.id == schedule.id
        assert persisted.jurisdiction == "san_francisco"
        assert persisted.paperwork == ["Application", "Floor Plan"]
        assert len(persisted.fees) == 2
        assert persisted.metadata["source"] == "fixture"


def test_write_fee_schedule_upserts_existing_record() -> None:
    first = write_fee_schedule(
        jurisdiction="oakland",
        paperwork=["Initial"],
        fees=[{"name": "Permit", "amount_cents": 10000}],
    )

    updated = write_fee_schedule(
        jurisdiction="oakland",
        paperwork=["Initial", "Follow-up"],
        fees=[{"name": "Permit", "amount_cents": 12000, "notes": "updated"}],
        notes="Revised",
        source_url="https://example.com/fees",
    )

    assert first.id == updated.id
    with SessionLocal() as session:
        stored = session.execute(
            select(FeeSchedule).where(FeeSchedule.jurisdiction == "oakland")
        ).scalar_one()
        assert stored.notes == "Revised"
        assert stored.source_url == "https://example.com/fees"
        assert stored.fees[0]["amount_cents"] == 12000


def test_write_reg_requirements_creates_and_updates_records() -> None:
    schedule = write_fee_schedule(
        jurisdiction="berkeley",
        paperwork=["Checklist"],
        fees=_sample_fee_items(),
    )

    created = write_reg_requirements(
        jurisdiction="berkeley",
        requirements=[
            {
                "requirement_id": "health-permit",
                "label": "Health Permit",
                "requirement_type": "Permit",
                "summary": "Submit application and pay fees",
                "documents": ["Application", "application"],
                "applies_to": ["Restaurants", "restaurants"],
                "tags": ["critical"],
                "metadata": {"agency": "DPH"},
                "fee_schedule": schedule,
                "status": "Active",
                "source_url": "https://example.com/permit",
            }
        ],
    )

    assert len(created) == 1
    requirement = created[0]
    assert requirement.external_id == "health-permit"
    assert requirement.requirement_type == "permit"
    assert requirement.documents == ["Application"]
    assert requirement.applies_to == ["Restaurants"]
    assert requirement.tags == ["critical"]
    assert requirement.metadata["agency"] == "DPH"
    assert requirement.fee_schedule_id == schedule.id

    updated = write_reg_requirements(
        jurisdiction="berkeley",
        requirements=[
            {
                "requirement_id": "health-permit",
                "label": "Health Permit Updated",
                "summary": "Updated guidance",
                "documents": ["Updated Form"],
                "applies_to": [],
                "metadata": {"agency": "DPH", "reviewed_at": "2024-03-01"},
                "tags": ["Critical", "featured"],
                "status": "updated",
            }
        ],
    )

    assert updated[0].label == "Health Permit Updated"
    assert updated[0].documents == ["Updated Form"]
    assert updated[0].applies_to == []
    assert set(updated[0].tags) == {"critical", "featured"}
    assert updated[0].status == "updated"
    assert "reviewed_at" in updated[0].metadata

    with SessionLocal() as session:
        persisted = session.execute(
            select(RegRequirement).where(RegRequirement.external_id == "health-permit")
        ).scalar_one()
        assert persisted.summary == "Updated guidance"
        assert persisted.fee_schedule_id == schedule.id


def test_write_reg_requirements_allows_existing_session() -> None:
    with SessionLocal() as session:
        schedule = write_fee_schedule(
            jurisdiction="palo_alto",
            paperwork=["Checklist"],
            fees=[{"name": "Permit", "amount_cents": 5000}],
            session=session,
        )
        write_reg_requirements(
            jurisdiction="palo_alto",
            requirements=[
                {
                    "requirement_id": "business-license",
                    "label": "Business License",
                    "metadata": {"agency": "City Clerk"},
                }
            ],
            fee_schedule_id=schedule.id,
            session=session,
        )
        session.flush()

        stored = session.execute(select(RegRequirement)).scalar_one()
        assert stored.fee_schedule_id == schedule.id


def test_write_reg_requirements_returns_empty_list_for_no_payload() -> None:
    assert write_reg_requirements(jurisdiction="sacramento", requirements=[]) == []
