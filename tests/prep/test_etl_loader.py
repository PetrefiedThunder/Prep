from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from etl.loader import load_regdocs
from prep.regulatory.models import RegDoc


@pytest.fixture()
def db_session() -> Session:
    """Provide an isolated in-memory SQLite session for each test."""

    engine = create_engine("sqlite:///:memory:", future=True)
    RegDoc.__table__.create(engine)

    with Session(engine) as session:
        yield session
        session.rollback()

    engine.dispose()


def test_load_regdocs_inserts_new_records(db_session: Session) -> None:
    rows = [
        {"sha256_hash": "abc", "title": "First doc"},
        {"sha256_hash": "def", "title": "Second doc", "state": "CA"},
    ]

    summary = load_regdocs(db_session, rows)

    assert summary == {"inserted": 2, "updated": 0, "skipped": 0}

    stored = db_session.execute(select(RegDoc).order_by(RegDoc.sha256_hash)).scalars().all()
    assert len(stored) == 2
    assert stored[0].title == "First doc"
    assert stored[1].state == "CA"


def test_load_regdocs_updates_existing_record(db_session: Session) -> None:
    initial = [{"sha256_hash": "abc", "title": "Original", "summary": "old"}]
    load_regdocs(db_session, initial)

    updated_payload = [
        {
            "sha256_hash": "abc",
            "title": "Original",
            "summary": "new summary",
            "city": "San Francisco",
        }
    ]

    summary = load_regdocs(db_session, updated_payload)

    assert summary == {"inserted": 0, "updated": 1, "skipped": 0}

    record = db_session.execute(select(RegDoc)).scalar_one()
    assert record.summary == "new summary"
    assert record.city == "San Francisco"


def test_load_regdocs_skips_invalid_or_unchanged(db_session: Session) -> None:
    load_regdocs(db_session, [{"sha256_hash": "abc", "title": "Persisted"}])

    summary = load_regdocs(
        db_session,
        [
            {"title": "Missing hash"},
            {"sha256_hash": "abc", "title": "Persisted"},
        ],
    )

    assert summary == {"inserted": 0, "updated": 0, "skipped": 2}

    record = db_session.execute(select(RegDoc)).scalar_one()
    assert record.title == "Persisted"
