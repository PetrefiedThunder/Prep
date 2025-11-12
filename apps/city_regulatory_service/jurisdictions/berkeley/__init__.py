"""Regulatory assets for Berkeley, California."""

from __future__ import annotations

from pathlib import Path
from typing import Final

JURISDICTION_NAME: Final = "Berkeley"
STATE: Final = "CA"
OPA_PACKAGE: Final = "city_regulatory_service.jurisdictions.berkeley"
OPA_POLICY_PATH: Final = Path(__file__).with_name("policy.rego")
DATA_SOURCE: Final = "City of Berkeley Public Health"
ALIASES: Final = (
    "berkeley",
    "berkeley, ca",
    "city of berkeley",
    "berkeley california",
)

__all__ = [
    "JURISDICTION_NAME",
    "STATE",
    "OPA_PACKAGE",
    "OPA_POLICY_PATH",
    "DATA_SOURCE",
    "ALIASES",
]
