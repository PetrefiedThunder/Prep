"""Tests for normalization scaffolding."""
from __future__ import annotations

from apps.ingestion_service.diff import diff_paragraphs
from apps.ingestion_service.normalize import build_paragraph, html_to_ast


def test_html_to_ast_returns_normalized_doc() -> None:
    doc = html_to_ast(b"<html><head><title>Sample</title></head><body></body></html>")
    assert doc.title == "Sample"
    assert doc.paragraphs == []


def test_build_paragraph_hashes_content() -> None:
    para = build_paragraph("p1", 1, "1", "Hello")
    assert para.hash is not None


def test_diff_paragraphs_detects_additions() -> None:
    para = build_paragraph("p1", 1, "1", "Hello")
    diff = diff_paragraphs([], [para])
    assert diff[0]["type"] == "added"
