"""Ensure the obligation schema contract is loadable."""
from __future__ import annotations

import json
from pathlib import Path


SCHEMA_PATH = Path("schemas/policy/obligation.schema.json")


def test_schema_contains_required_fields() -> None:
    data = json.loads(SCHEMA_PATH.read_text())
    required = set(data.get("required", []))
    assert {"obligation_id", "text_span_id", "provenance"}.issubset(required)
