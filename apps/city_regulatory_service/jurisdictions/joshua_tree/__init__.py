"""Regulatory assets for the Joshua Tree unincorporated community."""

from __future__ import annotations

from pathlib import Path
from typing import Final

JURISDICTION_NAME: Final = "Joshua Tree"
STATE: Final = "CA"
OPA_PACKAGE: Final = "city_regulatory_service.jurisdictions.joshua_tree"
OPA_POLICY_PATH: Final = Path(__file__).with_name("policy.rego")
DATA_SOURCE: Final = "San Bernardino County Land Use Services"
ALIASES: Final = (
    "joshua tree",
    "joshua tree, ca",
    "san bernardino county - joshua tree",
    "jt",
    "joshua tree national park gateway",
)

__all__ = [
    "JURISDICTION_NAME",
    "STATE",
    "OPA_PACKAGE",
    "OPA_POLICY_PATH",
    "DATA_SOURCE",
    "ALIASES",
]
