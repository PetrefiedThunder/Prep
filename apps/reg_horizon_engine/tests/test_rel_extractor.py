"""Tests for the relationship extractor."""
from __future__ import annotations

from reg_horizon_engine.parser import extract_relationships_from_akn
from reg_horizon_engine.standards.akn import akn_document


def _akn(text: str) -> bytes:
    return akn_document(
        {
            "eli": "/eli/eu/2025-01-01/dir/2025_123",
            "title": "Test",
            "jurisdiction": "eu",
            "doc_type": "dir",
            "date": "2025-01-01",
            "status": "proposed",
        },
        text,
    )


def test_cites_and_amends() -> None:
    xml = _akn(
        "This directive amends Regulation (EC) No 178/2002 and cites Directive 93/43/EEC."
    )
    relationships = extract_relationships_from_akn(
        "/eli/eu/2025-01-01/dir/2025_123", xml, "eu"
    )
    kinds = {relationship.rel.value for relationship in relationships}
    assert "amends" in kinds
    assert "cites" in kinds
    assert any("178/2002" in rel.snippet for rel in relationships)
