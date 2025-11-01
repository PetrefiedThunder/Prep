"""Helpers for constructing Akoma Ntoso documents for testing."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping

try:
    from lxml import etree
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs
    from xml.etree import ElementTree as etree  # type: ignore[no-redef]


def akn_document(metadata: Mapping[str, str], body_text: str) -> bytes:
    """Create a minimal Akoma Ntoso document for tests and fixtures."""

    akn = etree.Element("akomaNtoso")
    act = etree.SubElement(akn, "act")
    meta = etree.SubElement(act, "meta")
    identification = etree.SubElement(meta, "identification")
    for key, value in metadata.items():
        ref = etree.SubElement(identification, "FRBRexpression")
        ref.set("name", key)
        ref.set("value", value)
    body = etree.SubElement(act, "body")
    section = etree.SubElement(body, "section")
    paragraph = etree.SubElement(section, "paragraph")
    p = etree.SubElement(paragraph, "p")
    p.text = body_text
    etree.SubElement(meta, "generatedOn").text = datetime.now(timezone.utc).isoformat()
    return etree.tostring(akn)


__all__ = ["akn_document"]
