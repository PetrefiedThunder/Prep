"""Regulatory assets for Palo Alto, California."""
from __future__ import annotations

from pathlib import Path
from typing import Final

JURISDICTION_NAME: Final = "Palo Alto"
STATE: Final = "CA"
OPA_PACKAGE: Final = "city_regulatory_service.jurisdictions.palo_alto"
OPA_POLICY_PATH: Final = Path(__file__).with_name("policy.rego")
DATA_SOURCE: Final = "Palo Alto Development Services"
ALIASES: Final = (
    "palo alto",
    "palo alto, ca",
    "city of palo alto",
    "pa",
    "stanford area",
)

__all__ = [
    "JURISDICTION_NAME",
    "STATE",
    "OPA_PACKAGE",
    "OPA_POLICY_PATH",
    "DATA_SOURCE",
    "ALIASES",
]
