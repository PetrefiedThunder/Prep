"""Parsing helpers for regulatory documents."""

from __future__ import annotations

import logging
import re
from pathlib import Path

try:  # pragma: no cover - optional dependency in CI
    from pdfminer.high_level import extract_text as pdfminer_extract_text
except Exception:  # pragma: no cover - handled gracefully when missing
    pdfminer_extract_text = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency in CI
    from pdf2image import convert_from_path
except Exception:  # pragma: no cover - handled gracefully
    convert_from_path = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency in CI
    import pytesseract
except Exception:  # pragma: no cover - handled gracefully
    pytesseract = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_MIN_CHAR_THRESHOLD = 100
_SECTION_PATTERN = re.compile(r"^(?P<section>\d+-\d+\.\d+[A-Z]?)\s+(?P<heading>.+)$")


def _ocr_pdf(path: Path) -> str:
    if convert_from_path is None or pytesseract is None:
        return ""

    images = convert_from_path(str(path))
    try:
        text_chunks = [pytesseract.image_to_string(image) for image in images]
    finally:
        for image in images:
            try:
                image.close()
            except Exception:  # pragma: no cover - pillow may not expose close
                pass
    return "\n".join(chunk.strip() for chunk in text_chunks if chunk.strip())


def _ensure_pdfminer() -> None:
    if pdfminer_extract_text is None:
        raise ModuleNotFoundError(
            "pdfminer is required for pdf_to_text; install pdfminer.six to enable this feature"
        )


def pdf_to_text(path: str, *, min_chars: int = _MIN_CHAR_THRESHOLD) -> str:
    """Extract text from a PDF file, falling back to OCR when necessary."""

    _ensure_pdfminer()
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    assert pdfminer_extract_text is not None  # narrow type for type-checkers
    text = pdfminer_extract_text(str(pdf_path))
    if text and len(text.strip()) >= min_chars:
        return text

    logger.info("Primary PDF extraction yielded insufficient text; falling back to OCR")
    ocr_text = _ocr_pdf(pdf_path)
    return ocr_text or text


def extract_reg_sections(text: str) -> list[dict[str, str]]:
    """Split regulatory text into FDA-style sections."""

    sections: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current and current.get("body"):
                current["body"] += "\n"
            continue

        match = _SECTION_PATTERN.match(line)
        if match:
            if current:
                current["body"] = current.get("body", "").strip()
                sections.append(current)
            current = {
                "section": match.group("section"),
                "heading": match.group("heading").strip(),
                "body": "",
            }
            continue

        if current is None:
            logger.debug("Ignoring text outside of section: %s", line)
            continue

        if current["body"]:
            current["body"] = f"{current['body']} {line}".strip()
        else:
            current["body"] = line

    if current:
        current["body"] = current.get("body", "").strip()
        sections.append(current)

    return sections


__all__ = ["pdf_to_text", "extract_reg_sections"]
