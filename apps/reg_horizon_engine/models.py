"""Database models for the Regulatory Horizon Engine."""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import JSON, Date, DateTime, Float, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for ORM models."""


class RHESource(Base):
    """Tracked discovery source for regulatory documents."""

    __tablename__ = "rhe_sources"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, nullable=False, default=lambda: str(uuid4())
    )
    municipality_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    last_verified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RHEDocument(Base):
    """Parsed document metadata and content."""

    __tablename__ = "rhe_documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, nullable=False, default=lambda: str(uuid4())
    )
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    municipality_id: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entities: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(datetime.UTC)
    )


class RHEPrediction(Base):
    """Prediction metadata and rule deltas."""

    __tablename__ = "rhe_predictions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, nullable=False, default=lambda: str(uuid4())
    )
    municipality_id: Mapped[str] = mapped_column(String(255), nullable=False)
    bill_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    relevance: Mapped[float] = mapped_column(Float, nullable=False)
    prob_pass: Mapped[float] = mapped_column(Float, nullable=False)
    eta_enactment: Mapped[date | None] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text)
    change_diff: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(datetime.UTC)
    )
