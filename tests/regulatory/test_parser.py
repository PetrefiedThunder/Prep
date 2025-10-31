from __future__ import annotations

from importlib import util
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARSER_PATH = PROJECT_ROOT / "prep" / "regulatory" / "parser.py"
_SPEC = util.spec_from_file_location("prep_regulatory_parser", PARSER_PATH)
assert _SPEC and _SPEC.loader
_MODULE = util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
extract_reg_sections = _MODULE.extract_reg_sections


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text()


def test_extract_reg_sections_parses_fda_and_food_code_samples() -> None:
    text = "\n\n".join(
        [
            read_fixture("fda_sections.txt"),
            read_fixture("food_code_sections.txt"),
        ]
    )

    sections = extract_reg_sections(text)

    expected_sections = [
        "117.3",
        "117.4",
        "117.8",
        "117.80(b)(1)",
        "3-301.11",
        "3-302.12",
    ]
    assert [section["section"] for section in sections] == expected_sections

    expected_headings = [
        "Definitions.",
        "Personnel qualifications and training.",
        "Equipment and utensils",
        "Additional requirements for operations",
        "Preventing Contamination from Hands",
        "Preventing Contamination from Food",
    ]
    assert [section["heading"] for section in sections] == expected_headings

    assert sections[0]["body"].startswith(
        "This section introduces key terms and context for Subpart B."
    )
    assert "Additional detail line elaborating" in sections[0]["body"]
    assert sections[2]["body"].splitlines()[-1] == (
        "Sanitation schedules should reflect the complexity of the process."
    )
    assert sections[-2]["body"].startswith(
        "Food employees shall wash their hands to prevent contamination"
    )

    for section in sections:
        assert set(section.keys()) == {"section", "heading", "body"}
        assert section["body"]


def test_extract_reg_sections_returns_empty_for_text_without_identifiers() -> None:
    assert extract_reg_sections("General guidance without sections.") == []
"""Tests for the regulatory parser utilities."""

from __future__ import annotations

import importlib.util
import logging
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

pdfminer_module = ModuleType("pdfminer")
pdfminer_high_level = ModuleType("pdfminer.high_level")
pdfminer_pdfparser = ModuleType("pdfminer.pdfparser")


def _extract_text(path: str) -> str:
    data = Path(path).read_bytes().decode("latin-1")
    contents = re.findall(r"\(.*?\)", data)
    cleaned = [item[1:-1] for item in contents]
    return " ".join(cleaned)


class _PDFSyntaxError(Exception):
    pass


pdfminer_high_level.extract_text = _extract_text  # type: ignore[attr-defined]
pdfminer_pdfparser.PDFSyntaxError = _PDFSyntaxError

sys.modules["pdfminer"] = pdfminer_module
sys.modules["pdfminer.high_level"] = pdfminer_high_level
sys.modules["pdfminer.pdfparser"] = pdfminer_pdfparser

MODULE_SPEC = importlib.util.spec_from_file_location(
    "prep.regulatory.parser", Path(__file__).parents[2] / "prep" / "regulatory" / "parser.py"
)
assert MODULE_SPEC and MODULE_SPEC.loader
parser = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = parser
MODULE_SPEC.loader.exec_module(parser)


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def long_pdf(fixtures_dir: Path) -> Path:
    return fixtures_dir / "long_text.pdf"


@pytest.fixture
def short_pdf(fixtures_dir: Path) -> Path:
    return fixtures_dir / "short_text.pdf"


def test_pdf_to_text_returns_pdfminer_output(long_pdf: Path) -> None:
    text = parser.pdf_to_text(long_pdf)
    assert "PDFMiner-based extraction" in text
    assert len(text) >= 100


def test_pdf_to_text_falls_back_to_ocr(monkeypatch: pytest.MonkeyPatch, short_pdf: Path) -> None:
    original_find_spec = importlib.util.find_spec

    Image = pytest.importorskip("PIL.Image")

    def fake_find_spec(name: str):
        if name in {"pdf2image", "pytesseract"}:
            return object()
        return original_find_spec(name)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    pdf2image_module = ModuleType("pdf2image")

    def fake_convert(path: str):
        assert path == str(short_pdf)
        return [
            Image.new("RGB", (32, 32), color="white"),
            Image.new("RGB", (32, 32), color="black"),
        ]

    pdf2image_module.convert_from_path = fake_convert  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pdf2image", pdf2image_module)

    pytesseract_module = ModuleType("pytesseract")
    modes: list[str] = []

    def fake_image_to_string(image) -> str:
        modes.append(image.mode)
        return "OCR-text"

    pytesseract_module.image_to_string = fake_image_to_string  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pytesseract", pytesseract_module)

    result = parser.pdf_to_text(short_pdf, min_characters=999)
    assert result == "OCR-text\n\nOCR-text"
    assert modes == ["L", "L"]


def test_pdf_to_text_preprocesses_low_resolution_images(
    monkeypatch: pytest.MonkeyPatch,
    short_pdf: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    original_find_spec = importlib.util.find_spec

    Image = pytest.importorskip("PIL.Image")
    ImageFilter = pytest.importorskip("PIL.ImageFilter")

    def fake_find_spec(name: str):
        if name in {"pdf2image", "pytesseract"}:
            return object()
        return original_find_spec(name)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    pdf2image_module = ModuleType("pdf2image")

    def fake_convert(path: str):
        assert path == str(short_pdf)
        noisy = Image.effect_noise((40, 40), 120).filter(ImageFilter.GaussianBlur(1.2))
        return [noisy.convert("RGB")]

    pdf2image_module.convert_from_path = fake_convert  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pdf2image", pdf2image_module)

    pytesseract_module = ModuleType("pytesseract")
    processed_sizes: list[tuple[str, tuple[int, int]]] = []

    def fake_image_to_string(image) -> str:
        processed_sizes.append((image.mode, image.size))
        return "Pilot OCR text"

    pytesseract_module.image_to_string = fake_image_to_string  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pytesseract", pytesseract_module)

    caplog.set_level(logging.WARNING)

    result = parser.pdf_to_text(short_pdf, min_characters=999, pilot_mode=True)
    assert result == "Pilot OCR text"
    assert processed_sizes == [("L", (40, 40))]

    metrics_records = [
        record for record in caplog.records if getattr(record, "event", "") == "regulatory_pdf_ocr_metrics"
    ]
    assert metrics_records, "Expected structured OCR metrics when pilot_mode is enabled"
    metrics_record = metrics_records[0]
    assert metrics_record.total_characters == len(result)
    assert metrics_record.page_metrics
