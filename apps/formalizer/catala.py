"""Catala emitter stubs."""
from __future__ import annotations

from typing import Any


def obligation_to_catala(obj: dict[str, Any]) -> str:
    """Return a simple Catala-inspired snippet for the obligation."""

    subject = obj.get("subject", "subject")
    action = obj.get("action", "action")
    citation = obj.get("provenance", {}).get("para_hash", "unknown")
    return f"(* citation: {citation} *)\nlet {subject}_{action} = true"
