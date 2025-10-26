from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .orm import Base


# Default to fast, portable SQLite for tests; use DATABASE_URL in real envs.
def get_db_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")

engine = create_engine(
    get_db_url(),
    echo=bool(os.getenv("SQLA_ECHO")),
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

@contextmanager
def session_scope() -> Iterator:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create tables; safe for SQLite test runs."""
    Base.metadata.create_all(bind=engine)
