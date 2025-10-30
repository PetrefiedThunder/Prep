"""Document normalization stubs."""
from __future__ import annotations

import hashlib
try:  # pragma: no cover - optional dependency setup
    from bs4 import BeautifulSoup  # type: ignore
except ImportError:  # pragma: no cover - fallback path
    BeautifulSoup = None
from pydantic import BaseModel


class Paragraph(BaseModel):
    para_id: str
    level: int
    path: str
    text: str
    hash: str


class NormalizedDoc(BaseModel):
    doc_id: str
    jurisdiction: str
    title: str
    version: str
    published_at: str
    paragraphs: list[Paragraph]


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def html_to_ast(html: bytes) -> NormalizedDoc:
    """Convert HTML bytes into a normalized document.

    The implementation currently returns an empty scaffold. Concrete parsing
    logic should be added in subsequent iterations.
    """

    if BeautifulSoup is None:
        title = "Untitled"
    else:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else "Untitled"
    return NormalizedDoc(
        doc_id="",
        jurisdiction="",
        title=title or "Untitled",
        version="",
        published_at="",
        paragraphs=[],
    )


def pdf_to_ast(pdf: bytes) -> NormalizedDoc:  # pragma: no cover - stub
    """Convert PDF bytes into a normalized document."""

    raise NotImplementedError("PDF normalization not implemented")


def build_paragraph(para_id: str, level: int, path: str, text: str) -> Paragraph:
    """Helper to construct paragraph models with consistent hashing."""

    return Paragraph(
        para_id=para_id,
        level=level,
        path=path,
        text=text,
        hash=_hash_text(text),
    )
