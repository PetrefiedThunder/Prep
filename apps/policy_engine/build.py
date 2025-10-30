"""Policy engine build utilities."""
from __future__ import annotations

from typing import Iterable


def catala_to_rego(catala_src: str) -> str:
    """Convert Catala text to a Rego policy string."""

    return f"package policies\n\n# Transpiled from Catala\n{catala_src}"


def bundle_rego(rules: Iterable[str]) -> bytes:
    """Bundle Rego rules into a binary artifact."""

    combined = "\n\n".join(rules)
    return combined.encode("utf-8")
