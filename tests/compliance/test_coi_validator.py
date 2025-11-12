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

    monkeypatch.setattr("prep.compliance.coi_validator.convert_from_bytes", _convert)
    monkeypatch.setattr(
        "prep.compliance.coi_validator.pytesseract",
        SimpleNamespace(image_to_string=_image_to_string),
    )


def test_validate_coi_extracts_expected_fields(_mock_ocr: None) -> None:
    result = validate_coi(b"%PDF-sample")
    assert result["policy_number"] == "ABC-12345"
    assert result["insured_name"] == "Prep Kitchens LLC"
    assert result["expiry_date"] == "2035-12-31"
    assert "warnings" not in result


def test_validate_coi_raises_when_field_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Image:
        pass

    def _convert(_: bytes) -> list[_Image]:
        return [_Image()]

    def _image_to_string(_: _Image) -> str:
        return "Policy Number: XYZ\n"

    monkeypatch.setattr("prep.compliance.coi_validator.convert_from_bytes", _convert)
    monkeypatch.setattr(
        "prep.compliance.coi_validator.pytesseract",
        SimpleNamespace(image_to_string=_image_to_string),
    )

    with pytest.raises(COIExtractionError):
        validate_coi(b"%PDF-missing-fields")


def test_validate_coi_returns_warnings_in_pilot_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Image:
        pass

    def _convert(_: bytes) -> list[_Image]:
        return [_Image()]

    def _image_to_string(_: _Image) -> str:
        return "Named Insured: Prep Kitchens LLC\nExpiration Date: December 31, 2035\n"

    monkeypatch.setattr("prep.compliance.coi_validator.convert_from_bytes", _convert)
    monkeypatch.setattr(
        "prep.compliance.coi_validator.pytesseract",
        SimpleNamespace(image_to_string=_image_to_string),
    )

    result = validate_coi(b"%PDF-lenient", pilot_mode=True)
    assert result["policy_number"] is None
    assert result["insured_name"] == "Prep Kitchens LLC"
    assert result["expiry_date"] == "2035-12-31"
    assert "Policy number not found" in " ".join(result.get("warnings", []))


def test_validate_coi_allows_configurable_leniency(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Image:
        pass

    def _convert(_: bytes) -> list[_Image]:
        return [_Image()]

    def _image_to_string(_: _Image) -> str:
        return "Policy Number: ABC-9876\nExpiration Date: December 31, 2035\n"

    monkeypatch.setattr("prep.compliance.coi_validator.convert_from_bytes", _convert)
    monkeypatch.setattr(
        "prep.compliance.coi_validator.pytesseract",
        SimpleNamespace(image_to_string=_image_to_string),
    )

    with pytest.raises(COIExtractionError):
        validate_coi(b"%PDF-no-insured", pilot_mode=True, lenient_fields=("policy_number",))

    result = validate_coi(b"%PDF-no-insured", pilot_mode=True)
    assert result["insured_name"] is None
    assert any("Insured name" in warning for warning in result.get("warnings", []))
