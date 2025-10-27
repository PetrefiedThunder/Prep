from __future__ import annotations

from pathlib import Path

from etl import parser


def test_extract_sections_parses_fda_style_text():
    sample = """
    3-301.11 Preventing Contamination by Hands
    Food employees shall wash hands.
    (A) When switching tasks.

    3-302.12 Food Storage
    Store food at correct temperatures.
    """.strip()

    sections = parser.extract_reg_sections(sample)

    assert sections == [
        {
            "section": "3-301.11",
            "heading": "Preventing Contamination by Hands",
            "body": "Food employees shall wash hands. (A) When switching tasks.",
        },
        {
            "section": "3-302.12",
            "heading": "Food Storage",
            "body": "Store food at correct temperatures.",
        },
    ]


def test_pdf_to_text_falls_back_to_ocr(monkeypatch, tmp_path: Path):
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    monkeypatch.setattr(parser, "pdfminer_extract_text", lambda _: "tiny")
    monkeypatch.setattr(parser, "convert_from_path", lambda _: ["image1", "image2"])

    extracted_texts = {"image1": "First page", "image2": "Second page"}

    class DummyTesseract:
        def image_to_string(self, image):
            return extracted_texts[image]

    dummy = DummyTesseract()
    monkeypatch.setattr(parser, "pytesseract", dummy)

    result = parser.pdf_to_text(str(pdf_file), min_chars=10)
    assert result == "First page\nSecond page"


def test_pdf_to_text_returns_primary_when_sufficient(monkeypatch, tmp_path: Path):
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    monkeypatch.setattr(parser, "pdfminer_extract_text", lambda _: """This is adequate text.""")

    result = parser.pdf_to_text(str(pdf_file), min_chars=5)
    assert result == "This is adequate text."
