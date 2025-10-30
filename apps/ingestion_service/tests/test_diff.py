"""Focused tests for diff logic."""
from __future__ import annotations

from apps.ingestion_service.diff import diff_paragraphs
from apps.ingestion_service.normalize import build_paragraph


def test_diff_detects_removal() -> None:
    para = build_paragraph("p1", 1, "1", "Hello")
    diff = diff_paragraphs([para], [])
    assert diff[0]["type"] == "removed"
