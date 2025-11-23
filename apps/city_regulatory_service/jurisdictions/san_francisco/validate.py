"""Utilities for validating San Francisco permits with OPA."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any, Protocol

try:  # Optional dependency for isolated test environments
    import requests
except ModuleNotFoundError:  # pragma: no cover - lightweight shim for tests
    class _RequestsShim:
        def post(self, *args: object, **kwargs: object) -> None:  # pragma: no cover - replaced in tests
            raise ImportError("The 'requests' package is required for HTTP calls")

    requests = _RequestsShim()  # type: ignore


class SupportsJsonResponse(Protocol):
    """Protocol capturing the subset of :class:`requests.Response` we use."""

    def raise_for_status(self) -> None:
        """Raise an error if the HTTP response indicates failure."""

    def json(self) -> Any:  # pragma: no cover - exercised through tests
        """Return the JSON body of the response."""


def _serialize_for_opa(value: Any) -> Any:
    """Recursively convert values into an OPA-compatible JSON structure.

    ``datetime`` and ``date`` instances are converted to ISO 8601 strings so that
    ``requests`` can serialise the payload without errors.
    """

    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _serialize_for_opa(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_serialize_for_opa(item) for item in value]
    return value


def to_opa_input(data: Mapping[str, Any]) -> dict[str, Any]:
    """Prepare the payload that will be sent to OPA.

    The payload is wrapped in an ``input`` envelope to follow OPA's REST API
    expectations.
    """

    return {"input": _serialize_for_opa(data)}


def validate_permit(
    permit: Mapping[str, Any],
    *,
    opa_url: str,
    timeout: float = 5.0,
) -> Any:
    """Validate a permit by delegating the decision to an OPA policy endpoint."""

    payload = to_opa_input(permit)
    response = requests.post(opa_url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()
