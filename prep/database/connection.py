"""Lightweight async SQLAlchemy session utilities."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

def _normalize_database_url(url: str) -> str:
    """Ensure SQLite URLs use the async driver required by SQLAlchemy."""

    if url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    if url.startswith("sqlite+pysqlite://"):
        return url.replace("sqlite+pysqlite://", "sqlite+aiosqlite://", 1)
    return url


DATABASE_URL = _normalize_database_url(
    os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/prepchef")
)


def _engine_options(url: str) -> dict[str, Any]:
    echo_flag = os.getenv("SQLALCHEMY_ECHO", "0").lower() in {"1", "true", "on"}
    options: dict[str, Any] = {"echo": echo_flag}
    if url.startswith("sqlite"):
        return options
    options.update({"pool_size": 10, "max_overflow": 20})
    return options


engine = create_async_engine(DATABASE_URL, **_engine_options(DATABASE_URL))
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session."""

    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


__all__ = ["get_db", "AsyncSessionLocal", "engine"]
