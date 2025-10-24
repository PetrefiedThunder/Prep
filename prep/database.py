"""Database utilities for connecting to PostgreSQL using SQLAlchemy async."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://prep_admin:prep_admin@localhost:5432/prep",
)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a transactional session."""

    async with async_session_factory() as session:  # pragma: no cover - exercised via FastAPI
        try:
            yield session
        finally:
            await session.close()

