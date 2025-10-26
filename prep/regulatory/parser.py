"""Utilities for parsing regulatory documents."""

from __future__ import annotations

import re
from typing import Dict, List

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
