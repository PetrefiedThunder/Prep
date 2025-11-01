"""Data structures describing extracted legal relationships."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RelType(str, Enum):
    """Enumerated relationship types captured from regulations."""

    CITES = "cites"
    AMENDS = "amends"
    SUPERSEDES = "supersedes"
    TRANSPOSES = "transposes"


@dataclass(slots=True)
class Relationship:
    """Structured relationship record between two ELI references."""

    src_eli: str
    dst_eli: str
    rel: RelType
    snippet: str
    confidence: float
