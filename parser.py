"""Utilities for parsing PDF documents."""

from __future__ import annotations

from pathlib import Path

from pdfminer.high_level import extract_text


def pdf_to_text(path: str) -> str:
    """Return the textual contents of a PDF file located at ``path``.

    Parameters
    ----------
    path:
        The filesystem path to the PDF document.

    Returns
    -------
    str
        The extracted text contents of the PDF.

    Raises
    ------
    FileNotFoundError
        If the provided path does not exist or is not a file.
    """
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    return extract_text(str(pdf_path))
