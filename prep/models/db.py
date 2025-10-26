from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .orm import (
    Base,
    Booking,
    BookingStatus,
    COIDocument,
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


def _engine_kwargs(url: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"echo": _should_echo(), "future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
    return kwargs


_DATABASE_URL = get_db_url()
engine = create_engine(_DATABASE_URL, **_engine_kwargs(_DATABASE_URL))
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
    "COIDocument",
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
