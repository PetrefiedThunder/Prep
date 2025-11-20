from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio

pytest.importorskip("sqlalchemy")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from etl.loader import load_regdocs
from prep.models.orm import Base, RegDoc


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[RegDoc.__table__])
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_load_regdocs_insert_and_update(session: AsyncSession):
    rows = [
        {
            "jurisdiction": "ca",
            "code_section": "3-301.11",
            "requirement_text": "Wash hands",
            "effective_date": "2024-01-01",
            "citation_url": "https://example.com/a",
            "sha256_hash": "hash1",
        },
        {
            "jurisdiction": "ca",
            "code_section": "3-302.12",
            "requirement_text": "Store food cold",
            "sha256_hash": "hash2",
        },
    ]

    summary = await load_regdocs(session, rows)
    assert summary == {"inserted": 2, "updated": 0, "skipped": 0}

    result = await session.execute(select(RegDoc).order_by(RegDoc.code_section))
    stored = result.scalars().all()
    assert len(stored) == 2
    assert stored[0].effective_date == date(2024, 1, 1)

    updated_rows = [
        {
            "jurisdiction": "ca",
            "code_section": "3-301.11",
            "requirement_text": "Wash hands frequently",
            "effective_date": date(2024, 1, 1),
            "citation_url": "https://example.com/a",
            "sha256_hash": "hash1",
        },
        {
            "jurisdiction": "ca",
            "code_section": "3-302.12",
            "requirement_text": "Store food cold",
            "sha256_hash": "hash2",
        },
    ]

    summary = await load_regdocs(session, updated_rows)
    assert summary == {"inserted": 0, "updated": 1, "skipped": 1}

    result = await session.execute(select(RegDoc).where(RegDoc.sha256_hash == "hash1"))
    stored_doc = result.scalar_one()
    assert stored_doc.requirement_text == "Wash hands frequently"


@pytest.mark.asyncio
async def test_load_regdocs_validates_required_fields(session: AsyncSession):
    with pytest.raises(ValueError):
        await load_regdocs(session, [{"jurisdiction": "ca"}])
