"""Store-specific tables used by the Regulatory Horizon Engine."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, MetaData, String, Table, UniqueConstraint

from ...models import Base

metadata: MetaData = Base.metadata

lkg_nodes = Table(
    "lkg_nodes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("kind", String(32), nullable=False),
    Column("key", String(512), nullable=False, unique=True),
    Column("label", String(512), nullable=True),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    ),
)

lkg_edges = Table(
    "lkg_edges",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("src", Integer, ForeignKey("lkg_nodes.id", ondelete="CASCADE"), nullable=False),
    Column("dst", Integer, ForeignKey("lkg_nodes.id", ondelete="CASCADE"), nullable=False),
    Column("rel", String(32), nullable=False),
    Column("snippet", String(1024), nullable=True),
    Column("confidence", Float, nullable=False, default=0.0),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    ),
    UniqueConstraint("src", "dst", "rel", name="uq_lkg_edge"),
)

__all__ = ["lkg_nodes", "lkg_edges", "metadata"]
