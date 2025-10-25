"""Database utilities for the Prep platform."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from prep.settings import get_settings


def _engine_kwargs(settings) -> dict[str, Any]:
    return {
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_timeout": settings.database_pool_timeout,
        "pool_recycle": settings.database_pool_recycle,
        "pool_pre_ping": True,
        "echo": settings.is_development,
    }


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Return a shared async SQLAlchemy engine instance."""

    settings = get_settings()
    return create_async_engine(str(settings.database_url), future=True, **_engine_kwargs(settings))


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the configured async session factory."""

    engine = get_engine()
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a scoped async database session."""

    session_factory = get_session_factory()
    async with session_factory() as session:  # pragma: no branch - context managed
        try:
            yield session
        except Exception:  # pragma: no cover - allow rollback for calling code
            await session.rollback()
            raise
        finally:
            await session.close()
