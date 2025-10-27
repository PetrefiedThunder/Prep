"""Utilities for parsing regulatory documents."""

from __future__ import annotations

import re
from typing import Dict, List

# Regular expression matching section headings for common regulatory formats,
# including FDA CFR style identifiers (e.g. ``Sec. 117.8`` or ``§ 117.4``) and
# FDA Food Code identifiers (e.g. ``3-301.11``).
_SECTION_HEADING_RE = re.compile(
    r"""
    ^\s*
    (
        (?:(?:Sec\.?|Section|§)\s*)
        (?P<fda_section>\d+(?:\.\d+)*(?:\([A-Za-z0-9]+\))*)
        (?:\s*(?:[-–—]{1,2}|:)\s*|\s+)
        (?P<fda_heading>[^\n]+)
        |
        (?P<food_section>\d+-\d+(?:\.\d+)*(?:\([A-Za-z0-9]+\))*)
        \s+
        (?P<food_heading>[^\n]+)
    )
    """,
    flags=re.MULTILINE | re.VERBOSE | re.IGNORECASE,
)


def extract_reg_sections(text: str) -> List[Dict[str, str]]:
    """Extract regulatory sections from *text*.

    Parameters
    ----------
    text:
        Raw regulatory text that may contain sections like ``3-301.11`` or
        ``Sec. 117.8``.

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
        section_id = (
            match.group("fda_section")
            if match.group("fda_section") is not None
            else match.group("food_section")
        ).strip()
        heading = (
            match.group("fda_heading")
            if match.group("fda_heading") is not None
            else match.group("food_heading")
        ).strip()
        sections.append({
            "section": section_id,
            "heading": heading,
            "body": body,
        })

    return sections
