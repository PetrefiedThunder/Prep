"""Relationship extraction utilities."""

from .rel_extractor import extract_relationships_from_akn
from .structures import Relationship, RelType

__all__ = [
    "extract_relationships_from_akn",
    "Relationship",
    "RelType",
]
