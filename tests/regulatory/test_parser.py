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
