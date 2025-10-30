"""Retrieval augmented generation scaffolding."""
from __future__ import annotations

from typing import Any


def index_sections(sections: list[dict[str, Any]]) -> None:
    """Index section embeddings for later retrieval."""

    raise NotImplementedError("Embedding backend not implemented")


def retrieve_context(jurisdiction: str, query: str) -> list[dict[str, Any]]:
    """Retrieve contextual sections for obligation extraction."""

    raise NotImplementedError("Context retrieval not implemented")
