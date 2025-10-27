"""Unit tests for COI OCR extraction utilities."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from prep.compliance.coi_validator import COIExtractionError, validate_coi


@pytest.fixture()
def _mock_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide deterministic OCR behaviour for tests."""

    class _Image:
        pass

    dummy_image = _Image()

    def _convert(pdf_bytes: bytes) -> list[_Image]:
        assert pdf_bytes.startswith(b"%PDF"), "Expected PDF payload"
        return [dummy_image]

    def _image_to_string(image: _Image) -> str:
        assert image is dummy_image
        return (
            "Policy Number: ABC-12345\n"
            "Named Insured: Prep Kitchens LLC\n"
            "Expiration Date: December 31, 2035\n"
        )

    monkeypatch.setattr(
        "prep.compliance.coi_validator.convert_from_bytes", _convert
    )
    monkeypatch.setattr(
        "prep.compliance.coi_validator.pytesseract",
        SimpleNamespace(image_to_string=_image_to_string),
    )


def test_validate_coi_extracts_expected_fields(_mock_ocr: None) -> None:
    result = validate_coi(b"%PDF-sample")
    assert result["policy_number"] == "ABC-12345"
    assert result["insured_name"] == "Prep Kitchens LLC"
    assert result["expiry_date"] == "2035-12-31"


def test_validate_coi_raises_when_field_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Image:
        pass

    def _convert(_: bytes) -> list[_Image]:
        return [_Image()]

    def _image_to_string(_: _Image) -> str:
        return "Policy Number: XYZ\n"

    monkeypatch.setattr(
        "prep.compliance.coi_validator.convert_from_bytes", _convert
    )
    monkeypatch.setattr(
        "prep.compliance.coi_validator.pytesseract",
        SimpleNamespace(image_to_string=_image_to_string),
    )

    with pytest.raises(COIExtractionError):
        validate_coi(b"%PDF-missing-fields")
