"""Conversion helpers for LegalRuleML output."""
from __future__ import annotations

import json
from typing import Any


def obligation_to_legalruleml(obj: dict[str, Any]) -> str:
    """Serialize an obligation to a LegalRuleML-like string."""

    payload = {
        "obligation": obj,
        "metadata": {"format": "legalruleml", "version": "0.1"},
    }
    return json.dumps(payload)
