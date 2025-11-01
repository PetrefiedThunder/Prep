"""Relationship extraction from Akoma Ntoso documents."""
from __future__ import annotations

from typing import Iterable

try:
    from lxml import etree
    Element = etree._Element  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs
    from xml.etree import ElementTree as etree  # type: ignore[no-redef]

    Element = etree.Element  # type: ignore[attr-defined]

from .patterns import (
    AMENDS_PAT,
    CITES_PAT,
    DE_BGBl,
    DOC_TYPE_HINTS,
    EU_CITATION,
    FR_JO,
    SUPERSEDES_PAT,
    TRANSPOSES_PAT,
    UK_SI,
)
from .structures import Relationship, RelType
from ..standards.eli import ELI


def _guess_doc_type(label: str) -> str:
    for token, doc_type in DOC_TYPE_HINTS.items():
        if token.lower() in label.lower():
            return doc_type
    return "notice"


def _to_eli(jurisdiction: str, year: str, code: str, label: str) -> str:
    """Mint a lightweight ELI identifier when not explicitly provided."""

    doc_type = _guess_doc_type(label)
    natural_id = code.replace("/", "_")
    return ELI(
        jurisdiction=jurisdiction,
        date=f"{year}-01-01",
        doc_type=doc_type,
        natural_id=f"{year}_{natural_id}",
    ).iri()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _iter_text_nodes(root: Element) -> Iterable[str]:
    for element in root.iter():
        if _local_name(getattr(element, "tag", "")) in {"section", "paragraph", "p"}:
            text = " ".join(element.itertext()).strip()
            if text:
                yield text


def _match_citations(text: str, jurisdiction: str) -> list[tuple[str, str, int]]:
    pairs: list[tuple[str, str, int]] = []
    for match in EU_CITATION.finditer(text):
        token, code = match.group(1), match.group(2)
        year = code.split("/")[0] if "/" in code else "2000"
        pairs.append((match.group(0), _to_eli("eu", year, code, token), match.start()))
    for match in UK_SI.finditer(text):
        year, _serial = match.group(2).split("/")
        pairs.append((match.group(0), _to_eli("uk", year, match.group(2), "S.I."), match.start()))
    for match in FR_JO.finditer(text):
        number = match.group(2)
        year = number.split("-")[0] if "-" in number else "2000"
        pairs.append((match.group(0), _to_eli("fr", year, number, match.group(1)), match.start()))
    for match in DE_BGBl.finditer(text):
        code = match.group(2)
        year = code.split("/")[0] if "/" in code else "2000"
        pairs.append((match.group(0), _to_eli("de", year, code, match.group(1)), match.start()))
    return pairs


def _verb_positions(text: str) -> list[tuple[int, RelType]]:
    positions: list[tuple[int, RelType]] = []
    for pattern, rel in (
        (AMENDS_PAT, RelType.AMENDS),
        (SUPERSEDES_PAT, RelType.SUPERSEDES),
        (TRANSPOSES_PAT, RelType.TRANSPOSES),
        (CITES_PAT, RelType.CITES),
    ):
        for match in pattern.finditer(text):
            positions.append((match.start(), rel))
    positions.sort(key=lambda item: item[0])
    return positions


def extract_relationships_from_akn(
    eli: str,
    akn_xml: bytes | str,
    jurisdiction_hint: str,
) -> list[Relationship]:
    """Parse an Akoma Ntoso document and extract structural relationships."""

    if isinstance(akn_xml, str):
        akn_xml = akn_xml.encode("utf-8")
    root: Element = etree.fromstring(akn_xml)
    act = root.find(".//{*}act")
    if act is None:
        return []

    relationships: list[Relationship] = []
    for paragraph in _iter_text_nodes(act):
        targets = _match_citations(paragraph, jurisdiction_hint)
        if not targets:
            continue
        verb_spans = _verb_positions(paragraph)
        for snippet, dst_eli, start in targets:
            relation = RelType.CITES
            for pos, rel in verb_spans:
                if pos <= start:
                    relation = rel
                else:
                    break
            confidence = 0.85 if relation is not RelType.CITES else 0.75
            relationships.append(
                Relationship(
                    src_eli=eli,
                    dst_eli=dst_eli,
                    rel=relation,
                    snippet=snippet,
                    confidence=confidence,
                )
            )
    return relationships


__all__ = ["extract_relationships_from_akn"]
