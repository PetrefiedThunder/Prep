"""Database utilities for connecting to PostgreSQL using SQLAlchemy async."""
"""Database utilities for the Prep platform."""

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
from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

DEFAULT_DATABASE_URL = "postgresql+asyncpg://prep:prep@localhost:5432/prep"


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Return a shared async SQLAlchemy engine instance."""

    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    return create_async_engine(database_url, future=True, echo=False)


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the configured async session factory."""

    engine = get_engine()
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a scoped async database session."""

    session_factory = get_session_factory()
    async with session_factory() as session:  # pragma: no branch - context managed
        try:
            yield session
        finally:
            await session.close()

