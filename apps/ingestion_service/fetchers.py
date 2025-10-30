"""Fetch helpers for different source types."""
from __future__ import annotations

from typing import Any


def fetch_html(url: str) -> bytes:
    """Fetch raw HTML from the provided URL."""

    raise NotImplementedError("HTML fetching not implemented")


def fetch_pdf(url: str) -> bytes:
    """Fetch raw PDF bytes from the provided URL."""

    raise NotImplementedError("PDF fetching not implemented")


def fetch_rss(url: str) -> list[dict[str, Any]]:
    """Fetch and parse an RSS feed."""

    raise NotImplementedError("RSS fetching not implemented")


def fetch_api(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """Call a structured API endpoint."""

    raise NotImplementedError("API fetching not implemented")
