"""Regular expressions used to detect citations and relationships."""
from __future__ import annotations

import re

# Language-aware citation/relationship patterns (expandable)
EU_CITATION = re.compile(
    r"(Regulation|Directive|Decision)\s*(?:\((?:EU|EC)\))?\s*(?:No\s*)?([0-9]{2,4}/[0-9]{1,4})",
    re.IGNORECASE,
)
UK_SI = re.compile(r"(S\.I\.)\s*([0-9]{4}/[0-9]+)", re.IGNORECASE)
FR_JO = re.compile(r"(décret|arrêté)\s+n[°º]\s*([0-9\-]+)", re.IGNORECASE)
DE_BGBl = re.compile(r"(Verordnung|Gesetz)\s*(?:\(BGBl\.\))?\s*(?:Nr\.)?\s*([0-9/]+)", re.IGNORECASE)

AMENDS_PAT = re.compile(r"\b(amends?|modif(?:y|ies|iziert)|ersetzt|abroge)\b", re.IGNORECASE)
SUPERSEDES_PAT = re.compile(
    r"\b(supersed(?:e|es)|repeal(?:s|ed)|aufgehoben)\b",
    re.IGNORECASE,
)
TRANSPOSES_PAT = re.compile(
    r"\b(transpos(?:e|es|ition)|umsetz(?:t|ung))\b",
    re.IGNORECASE,
)
CITES_PAT = re.compile(r"\b(cites?|refer(?:s|red|ring)?)\b", re.IGNORECASE)

# Map a matched token to a doc_type hint
DOC_TYPE_HINTS = {
    "Regulation": "reg",
    "Directive": "dir",
    "Decision": "dec",
    "S.I.": "si",
    "décret": "decret",
    "arrêté": "arrete",
    "Verordnung": "ordnung",
    "Gesetz": "gesetz",
}

__all__ = [
    "EU_CITATION",
    "UK_SI",
    "FR_JO",
    "DE_BGBl",
    "AMENDS_PAT",
    "SUPERSEDES_PAT",
    "TRANSPOSES_PAT",
    "CITES_PAT",
    "DOC_TYPE_HINTS",
]
