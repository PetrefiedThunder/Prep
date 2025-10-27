"""Tests for regulatory loader normalization helpers."""

from prep.regulatory.loader import _normalize_regdoc


def test_normalize_regdoc_sets_defaults() -> None:
    payload = {
        "sha256_hash": "abc123",
        "title": "Sample",
        "state": "CA",
    }

    normalized = _normalize_regdoc(payload)

    assert normalized["country_code"] == "US"
    assert normalized["state_province"] == "CA"
    assert normalized["raw_payload"]["sha256_hash"] == "abc123"


def test_normalize_regdoc_respects_explicit_fields() -> None:
    payload = {
        "sha256_hash": "def456",
        "country_code": "CA",
        "state_province": "ON",
        "state": "CA",
    }

    normalized = _normalize_regdoc(payload)

    assert normalized["country_code"] == "CA"
    assert normalized["state_province"] == "ON"
