from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator[uuid.UUID]):
    """Platform-agnostic GUID/UUID type."""
"""Platform-independent GUID/UUID database type utilities."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type.

    Uses PostgreSQL's native UUID type with ``as_uuid=True`` while falling back to
    ``CHAR(36)`` for dialects such as SQLite that lack UUID support. Values are
    converted to :class:`uuid.UUID` instances on load to provide a consistent API.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect):  # type: ignore[override]
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value: Any, dialect):  # type: ignore[override]
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Optional[Any], dialect):  # type: ignore[override]
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value if dialect.name == "postgresql" else str(value)
        parsed = uuid.UUID(str(value))
        return parsed if dialect.name == "postgresql" else str(parsed)

    def process_result_value(self, value: Optional[Any], dialect):  # type: ignore[override]
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


__all__ = ["GUID"]
