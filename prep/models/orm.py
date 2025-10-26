from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, declared_attr
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from prep.models.guid import GUID


class Base(DeclarativeBase):
    """Declarative base with predictable table naming."""

    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore[override]
        # snake_case by default
        import re

        name = cls.__name__
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
