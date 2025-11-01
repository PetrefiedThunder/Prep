"""Codifier utilities for generating JSONPatch diffs."""
from __future__ import annotations

from typing import Any

import jsonpatch


def parse_rules(raw_text: str) -> dict[str, Any]:
    """Convert ordinance text into a normalized rule graph.

    The parsing strategy is a placeholder. Production implementations should
    rely on the primary regengine parsing stack to transform legal text into
    machine-actionable structures.
    """

    return {"raw_text": raw_text}


def generate_diff(current_text: str, proposed_text: str) -> list[dict[str, Any]]:
    """Return a JSONPatch diff between current and proposed regulations."""

    current_rules = parse_rules(current_text)
    proposed_rules = parse_rules(proposed_text)
    patch = jsonpatch.JsonPatch.from_diff(current_rules, proposed_rules)
    return list(patch)
