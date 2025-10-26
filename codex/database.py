"""Database utilities for the Codex backend."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings


def _engine_kwargs(settings) -> dict[str, Any]:
    """Return engine keyword arguments based on the configured backend."""

    url = settings.database_url
    kwargs: dict[str, Any] = {"echo": settings.database_echo, "pool_pre_ping": True}
    if url.startswith("sqlite+"):
        # SQLite's async drivers rely on a NullPool so we avoid extra pooling options.
        kwargs.pop("pool_pre_ping", None)
    else:
        kwargs.update(
            {
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "pool_timeout": settings.database_pool_timeout,
                "pool_recycle": settings.database_pool_recycle,
            }
        )
    return kwargs


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Return a cached async SQLAlchemy engine instance."""

    settings = get_settings()
    return create_async_engine(settings.database_url, future=True, **_engine_kwargs(settings))


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the configured async session factory."""

    engine = get_engine()
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional scope for database interactions."""

    session_factory = get_session_factory()
    async with session_factory() as session:  # pragma: no branch - managed context
        try:
            yield session
            await session.commit()
        except Exception:  # pragma: no cover - rollback path
            await session.rollback()
            raise


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-style dependency that yields a session without auto commit."""

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:  # pragma: no cover - rollback for consumer errors
            await session.rollback()
            raise


def reset_engine_cache() -> None:
    """Clear cached engine and session factory instances."""

    get_engine.cache_clear()
    get_session_factory.cache_clear()


__all__ = [
    "get_engine",
    "get_session_factory",
    "get_session",
    "reset_engine_cache",
    "session_scope",
]
