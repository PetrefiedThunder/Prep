"""Utilities for validating Palo Alto permits with OPA."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import requests

from apps.city_regulatory_service.jurisdictions.san_francisco import validate as sf_validate

SupportsJsonResponse = sf_validate.SupportsJsonResponse


def to_opa_input(data: Mapping[str, Any]) -> dict[str, Any]:
    """Prepare an OPA payload using the shared serializer."""

    return sf_validate.to_opa_input(data)


def validate_permit(
    permit: Mapping[str, Any],
    *,
    opa_url: str,
    timeout: float = 5.0,
) -> Any:
    """Validate a Palo Alto permit by delegating to an OPA policy endpoint."""

    payload = to_opa_input(permit)
    response = requests.post(opa_url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


__all__ = ["SupportsJsonResponse", "to_opa_input", "validate_permit"]
