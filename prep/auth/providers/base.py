"""Shared data structures for identity provider integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(slots=True)
class IdentityAssertion:
    """Normalized identity attributes resolved from an IdP assertion."""

    subject: str
    email: str | None = None
    full_name: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)


__all__ = ["IdentityAssertion"]
