from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .orm import (
    Base,
    Booking,
    BookingStatus,
    InventoryItem,
    InventoryLot,
    InventoryTransfer,
    InventoryTransferStatus,
    VerificationTask,
    VerificationTaskStatus,
    COIDocument,
    CertificationDocument,
    CertificationReviewStatus,
    COIDocument,
    ComplianceDocument,
    ComplianceDocumentStatus,
    ChecklistTemplate,
    SubleaseContract,
    SubleaseContractStatus,
    Kitchen,
    KitchenModerationEvent,
    Supplier,
    ModerationStatus,
    Review,
    ReviewFlag,
    ReviewFlagStatus,
    ReviewPhoto,
    ReviewStatus,
    ReviewVote,
    RecurringBookingTemplate,
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
    # Import modules that define additional models to ensure they are registered
    # on the global SQLAlchemy metadata before creating tables.
    import prep.regulatory.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


__all__ = [
    "Base",
    "Booking",
    "BookingStatus",
    "InventoryItem",
    "InventoryLot",
    "InventoryTransfer",
    "InventoryTransferStatus",
    "VerificationTask",
    "VerificationTaskStatus",
    "COIDocument",
    "CertificationDocument",
    "CertificationReviewStatus",
    "ComplianceDocument",
    "ComplianceDocumentStatus",
    "ChecklistTemplate",
    "SubleaseContract",
    "SubleaseContractStatus",
    "Kitchen",
    "KitchenModerationEvent",
    "Supplier",
    "ModerationStatus",
    "Review",
    "ReviewFlag",
    "ReviewFlagStatus",
    "ReviewPhoto",
    "ReviewStatus",
    "ReviewVote",
    "RecurringBookingTemplate",
    "SessionLocal",
    "User",
    "UserRole",
    "engine",
    "get_db_url",
    "init_db",
    "session_scope",
]
