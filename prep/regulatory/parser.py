"""Utilities for parsing regulatory documents."""

from __future__ import annotations

import importlib.util
import logging
import re
import time
from contextlib import suppress
from pathlib import Path
from typing import Dict, List

# Regular expression matching section headings for common regulatory formats,
# including FDA CFR style identifiers (e.g. ``Sec. 117.8`` or ``§ 117.4``) and
# FDA Food Code identifiers (e.g. ``3-301.11``).
from pdfminer.high_level import extract_text
from pdfminer.pdfparser import PDFSyntaxError


LOGGER = logging.getLogger(__name__)

# Regular expression matching Food Code style section headings. These typically
# look like ``3-301.11 Preventing Contamination from Hands`` where the numeric
# identifier always begins a new line.
_SECTION_HEADING_RE = re.compile(
    r"""
    ^\s*
    (
        (?:(?:Sec\.?|Section|§)\s*)
        (?P<fda_section>\d+(?:\.\d+)*(?:\([A-Za-z0-9]+\))*)
        (?:\s*(?:[-–—]{1,2}|:)\s*|\s+)
        (?P<fda_heading>[^\n]+)
        |
        (?P<food_section>\d+-\d+(?:\.\d+)*(?:\([A-Za-z0-9]+\))*)
        \s+
        (?P<food_heading>[^\n]+)
    )
    """,
    flags=re.MULTILINE | re.VERBOSE | re.IGNORECASE,
)


def extract_reg_sections(text: str) -> List[Dict[str, str]]:
    """Extract regulatory sections from *text*.

    Parameters
    ----------
    text:
        Raw regulatory text that may contain sections like ``3-301.11`` or
        ``Sec. 117.8``.

    Returns
    -------
    list of dict
        A list of dictionaries with ``section``, ``heading`` and ``body`` keys
        describing each identified section. The ``body`` contains the text up to
        (but not including) the next detected section.
    """

    if not text:
        return []

    matches = list(_SECTION_HEADING_RE.finditer(text))
    sections: List[Dict[str, str]] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        section_id = (
            match.group("fda_section")
            if match.group("fda_section") is not None
            else match.group("food_section")
        ).strip()
        heading = (
            match.group("fda_heading")
            if match.group("fda_heading") is not None
            else match.group("food_heading")
        ).strip()
        sections.append({
            "section": section_id,
            "heading": heading,
            "body": body,
        })

    return sections


def _prepare_for_ocr(image):
    """Return an image processed for OCR consumption."""

    try:
        from PIL import ImageEnhance, ImageFilter, ImageOps  # type: ignore
    except Exception:  # pragma: no cover - fallback when Pillow unavailable
        return image

    processed = ImageOps.grayscale(image)
    processed = ImageEnhance.Contrast(processed).enhance(1.5)
    processed = processed.filter(ImageFilter.MedianFilter(size=3))
    return processed


def pdf_to_text(
    pdf_path: str | Path,
    *,
    min_characters: int = 100,
    pilot_mode: bool = False,
    log: logging.Logger | None = None,
) -> str:
    """Return text extracted from *pdf_path* using PDFMiner with OCR fallback.

    Parameters
    ----------
    pdf_path:
        Path to the PDF document.
    min_characters:
        Minimum number of characters required to trust the PDFMiner output. If
        the extracted text is shorter than this threshold, an OCR pass using
        ``pytesseract`` is attempted when the optional dependencies are
        available.
    """

    logger = log or LOGGER

    path = Path(pdf_path)

    try:
        extracted_text = extract_text(str(path)).strip()
    except PDFSyntaxError:
        extracted_text = ""

    if len(extracted_text) >= min_characters:
        if pilot_mode:
            logger.info(
                "pdfminer_extraction_sufficient",
                extra={
                    "event": "regulatory_pdfminer_success",
                    "pdf_path": str(path),
                    "character_count": len(extracted_text),
                    "pilot_mode": True,
                },
            )
        return extracted_text

    pdf2image_spec = importlib.util.find_spec("pdf2image")
    pytesseract_spec = importlib.util.find_spec("pytesseract")

    if pdf2image_spec is None or pytesseract_spec is None:
        if pilot_mode:
            logger.warning(
                "ocr_dependencies_missing",
                extra={
                    "event": "regulatory_pdf_ocr_unavailable",
                    "pdf_path": str(path),
                    "missing_dependencies": [
                        name
                        for name, spec in (
                            ("pdf2image", pdf2image_spec),
                            ("pytesseract", pytesseract_spec),
                        )
                        if spec is None
                    ],
                    "pilot_mode": True,
                },
            )
        return extracted_text

    from pdf2image import convert_from_path  # type: ignore
    import pytesseract  # type: ignore

    if pilot_mode:
        logger.warning(
            "pdfminer_extraction_insufficient",
            extra={
                "event": "regulatory_pdfminer_fallback",
                "pdf_path": str(path),
                "character_count": len(extracted_text),
                "min_characters": min_characters,
                "pilot_mode": True,
            },
        )

    try:
        images = convert_from_path(str(path))
    except Exception as exc:
        if pilot_mode:
            logger.warning(
                "ocr_conversion_failed",
                extra={
                    "event": "regulatory_pdf_ocr_conversion_failed",
                    "pdf_path": str(path),
                    "error": str(exc),
                    "pilot_mode": True,
                },
            )
        return extracted_text

    ocr_segments: List[str] = []
    page_metrics: List[Dict[str, object]] = []
    for index, image in enumerate(images):
        preprocess_start = time.perf_counter()
        processed_image = _prepare_for_ocr(image)
        preprocess_duration_ms = (time.perf_counter() - preprocess_start) * 1000

        try:
            ocr_result = pytesseract.image_to_string(processed_image).strip()
        except Exception as exc:
            if pilot_mode:
                page_metrics.append(
                    {
                        "page_index": index,
                        "preprocess_ms": round(preprocess_duration_ms, 2),
                        "error": str(exc),
                    }
                )
                logger.warning(
                    "ocr_page_failed",
                    extra={
                        "event": "regulatory_pdf_ocr_page_failed",
                        "pdf_path": str(path),
                        "page_index": index,
                        "error": str(exc),
                        "pilot_mode": True,
                    },
                )
            continue

        char_count = len(ocr_result)
        if ocr_result:
            ocr_segments.append(ocr_result)

        if pilot_mode:
            metric_entry: Dict[str, object] = {
                "page_index": index,
                "preprocess_ms": round(preprocess_duration_ms, 2),
                "ocr_characters": char_count,
            }
            if not ocr_result:
                metric_entry["note"] = "empty_ocr_output"
            page_metrics.append(metric_entry)

        for candidate in (processed_image, image):
            with suppress(Exception):
                if hasattr(candidate, "close"):
                    candidate.close()

    if not ocr_segments:
        if pilot_mode:
            logger.warning(
                "ocr_no_text_extracted",
                extra={
                    "event": "regulatory_pdf_ocr_empty",
                    "pdf_path": str(path),
                    "page_count": len(images),
                    "pilot_mode": True,
                },
            )
        return extracted_text

    if pilot_mode:
        logger.warning(
            "ocr_metrics",
            extra={
                "event": "regulatory_pdf_ocr_metrics",
                "pdf_path": str(path),
                "page_count": len(images),
                "processed_pages": len(page_metrics),
                "pages_with_text": len(ocr_segments),
                "total_characters": sum(len(segment) for segment in ocr_segments),
                "page_metrics": page_metrics,
                "pilot_mode": True,
            },
        )

    return "\n\n".join(ocr_segments)
