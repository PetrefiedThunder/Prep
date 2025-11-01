"""Database helpers for the San Francisco regulatory service."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL_ENV = "SF_DATABASE_URL"
DEFAULT_DATABASE_URL = "sqlite:///./sf_regulatory_service.db"

Base = declarative_base()


def _create_engine() -> Engine:
    database_url = os.getenv(DATABASE_URL_ENV, DEFAULT_DATABASE_URL)
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            future=True,
        )
    return create_engine(database_url, future=True)


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def init_db() -> None:
    """Create database tables if they do not already exist."""
    from . import models  # noqa: WPS433  (import for side-effects)

    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - re-raise for FastAPI error handling
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a database session."""
    with session_scope() as session:
        yield session
