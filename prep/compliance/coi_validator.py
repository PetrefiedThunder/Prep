"""Utilities for validating Certificates of Insurance (COI)."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Dict, Iterable

try:  # pragma: no cover - import guarded for optional dependency environments
    from pdf2image import convert_from_bytes
except ImportError:  # pragma: no cover - handled at runtime when function is invoked
    convert_from_bytes = None  # type: ignore[assignment]

try:  # pragma: no cover - import guarded for optional dependency environments
    import pytesseract
except ImportError:  # pragma: no cover - handled at runtime when function is invoked
    pytesseract = None  # type: ignore[assignment]


_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
)


class COIExtractionError(ValueError):
    """Raised when a Certificate of Insurance is missing required fields."""


def _normalise_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _parse_expiry(raw_value: str) -> str:
    cleaned = raw_value.strip()
    cleaned = re.sub(r"[^0-9A-Za-z,\/\- ]", "", cleaned)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    raise COIExtractionError("Unable to parse expiry date from COI document.")


def validate_coi(
    pdf_bytes: bytes,
    *,
    pilot_mode: bool = False,
    lenient_fields: Iterable[str] | None = None,
) -> Dict[str, str | None | list[str]]:
    """Extract key fields from a Certificate of Insurance PDF.

    Args:
        pdf_bytes: The raw bytes of the COI PDF.

    Returns:
        A dictionary containing the policy number, insured name, and expiry date.

    Raises:
        ValueError: If the PDF cannot be processed or any required field is missing.
    """

    if not pdf_bytes:
        raise COIExtractionError("No PDF data supplied for COI validation.")

    lenient_set = {
        field.lower()
        for field in (lenient_fields if lenient_fields is not None else ("policy_number", "insured_name"))
    }

    missing_dependencies = []
    if convert_from_bytes is None:
        missing_dependencies.append("pdf2image")
    if pytesseract is None:
        missing_dependencies.append("pytesseract")
    if missing_dependencies:
        deps = ", ".join(missing_dependencies)
        raise COIExtractionError(
            f"Required dependencies missing for COI validation: {deps}."
        )

    try:
        images = convert_from_bytes(pdf_bytes)  # type: ignore[misc]
    except Exception as exc:  # pragma: no cover - defensive against pdf2image errors
        raise COIExtractionError("Unable to read COI PDF bytes.") from exc

    if not images:
        raise COIExtractionError("COI PDF does not contain any pages.")

    text_chunks = []
    for image in images:
        text = pytesseract.image_to_string(image)  # type: ignore[call-arg]
        if text:
            text_chunks.append(text)

    full_text = "\n".join(text_chunks)
    if not full_text.strip():
        raise COIExtractionError("Unable to extract text from COI document.")

    policy_patterns = (
        r"policy\s*(?:number|no\.?|#)\s*[:\-#]?\s*([A-Z0-9\-\/]+)",
        r"policy\s*[:\-#]?\s*([A-Z0-9\-\/]+)",
    )
    insured_patterns = (
        r"(?:named\s+)?insured\s*(?:name)?\s*[:\-]?\s*(.+)",
        r"certificate\s+holder\s*[:\-]?\s*(.+)",
    )
    expiry_patterns = (
        r"(?:expiration|expiry|expires)\s*(?:date)?\s*[:\-]?\s*([A-Za-z0-9,\-/ ]+)",
        r"exp\.\s*date\s*[:\-]?\s*([A-Za-z0-9,\-/ ]+)",
    )

    def _extract(patterns: tuple[str, ...]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                value = value.split("\n", 1)[0]
                return _normalise_whitespace(value)
        return None

    warnings: list[str] = []

    policy_number = _extract(policy_patterns)
    if not policy_number:
        message = "Policy number not found in COI document."
        if pilot_mode and "policy_number" in lenient_set:
            warnings.append(message)
        else:
            raise COIExtractionError(message)

    insured_name = _extract(insured_patterns)
    if not insured_name:
        message = "Insured name not found in COI document."
        if pilot_mode and "insured_name" in lenient_set:
            warnings.append(message)
        else:
            raise COIExtractionError(message)

    expiry_raw = _extract(expiry_patterns)
    if not expiry_raw:
        raise COIExtractionError("Expiry date not found in COI document.")

    expiry_date = _parse_expiry(expiry_raw)

    result: Dict[str, str | None | list[str]] = {
        "policy_number": policy_number,
        "insured_name": insured_name,
        "expiry_date": expiry_date,
    }
    if pilot_mode:
        result["warnings"] = warnings

    return result


__all__ = ["validate_coi", "COIExtractionError"]
