"""Regulatory assets for San Jose, California."""
from __future__ import annotations

from pathlib import Path
from typing import Final

JURISDICTION_NAME: Final = "San Jose"
STATE: Final = "CA"
OPA_PACKAGE: Final = "city_regulatory_service.jurisdictions.san_jose"
OPA_POLICY_PATH: Final = Path(__file__).with_name("policy.rego")
DATA_SOURCE: Final = "San Jose Environmental Services Department"
ALIASES: Final = (
    "san jose",
    "san jose, ca",
    "city of san jose",
    "sj",
    "silicon valley",
)

__all__ = [
    "JURISDICTION_NAME",
    "STATE",
    "OPA_PACKAGE",
    "OPA_POLICY_PATH",
    "DATA_SOURCE",
    "ALIASES",
]
