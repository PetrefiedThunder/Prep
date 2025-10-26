from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .orm import (
    Base,
    Booking,
    BookingStatus,
    CertificationDocument,
    CertificationReviewStatus,
    ComplianceDocument,
    ComplianceDocumentStatus,
    Kitchen,
    KitchenModerationEvent,
    ModerationStatus,
    Review,
    ReviewFlag,
    ReviewFlagStatus,
    ReviewPhoto,
    ReviewStatus,
    ReviewVote,
    User,
    UserRole,
)


def get_db_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")


def _should_echo() -> bool:
    value = os.getenv("SQLA_ECHO")
    if value is None:
        return False
    return value.lower() in {"1", "true", "yes", "on"}


engine = create_engine(get_db_url(), echo=_should_echo(), future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope() -> Iterator:
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
    Base.metadata.create_all(bind=engine)


__all__ = [
    "Base",
    "Booking",
    "BookingStatus",
    "CertificationDocument",
    "CertificationReviewStatus",
    "ComplianceDocument",
    "ComplianceDocumentStatus",
    "Kitchen",
    "KitchenModerationEvent",
    "ModerationStatus",
    "Review",
    "ReviewFlag",
    "ReviewFlagStatus",
    "ReviewPhoto",
    "ReviewStatus",
    "ReviewVote",
    "SessionLocal",
    "User",
    "UserRole",
    "engine",
    "get_db_url",
    "init_db",
    "session_scope",
]
