"""Utilities for parsing regulatory documents."""

from __future__ import annotations

from pathlib import Path
import importlib.util
import re
from typing import Dict, List

from pdfminer.high_level import extract_text
from pdfminer.pdfparser import PDFSyntaxError

# Regular expression matching Food Code style section headings. These typically
# look like ``3-301.11 Preventing Contamination from Hands`` where the numeric
# identifier always begins a new line.
_SECTION_HEADING_RE = re.compile(
    r"^\s*(?P<section>\d+-\d+(?:\.\d+)*(?:\([A-Za-z0-9]+\))*)\s+"
    r"(?P<heading>[^\n]+)",
    flags=re.MULTILINE,
)


def extract_reg_sections(text: str) -> List[Dict[str, str]]:
    """Extract Food Code style regulatory sections from *text*.

    Parameters
    ----------
    text:
        Raw regulatory text that may contain sections like ``3-301.11``.

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
        section_id = match.group("section").strip()
        heading = match.group("heading").strip()
        sections.append({
            "section": section_id,
            "heading": heading,
            "body": body,
        })

    return sections


def pdf_to_text(pdf_path: str | Path, *, min_characters: int = 100) -> str:
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

    path = Path(pdf_path)

    try:
        extracted_text = extract_text(str(path)).strip()
    except PDFSyntaxError:
        extracted_text = ""

    if len(extracted_text) >= min_characters:
        return extracted_text

    pdf2image_spec = importlib.util.find_spec("pdf2image")
    pytesseract_spec = importlib.util.find_spec("pytesseract")

    if pdf2image_spec is None or pytesseract_spec is None:
        return extracted_text

    from pdf2image import convert_from_path  # type: ignore
    import pytesseract  # type: ignore

    try:
        images = convert_from_path(str(path))
    except Exception:
        return extracted_text

    ocr_segments: List[str] = []
    for image in images:
        try:
            ocr_result = pytesseract.image_to_string(image).strip()
        except Exception:
            continue
        if ocr_result:
            ocr_segments.append(ocr_result)

    if not ocr_segments:
        return extracted_text

    return "\n\n".join(ocr_segments)
