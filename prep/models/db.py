from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from prep.models.guid import GUID


class Base(DeclarativeBase):
    """Declarative base class."""

    pass


class UserRole(str, enum.Enum):
    """Supported user roles within the Prep platform."""

    HOST = "host"
    ADMIN = "admin"
    CUSTOMER = "customer"


class ModerationStatus(str, enum.Enum):
    """Workflow state for kitchen moderation."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"

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
