"""Utility helpers for resolving jurisdiction metadata."""

from __future__ import annotations

_KNOWN_ZIP_CODES: dict[str, dict[str, str | None]] = {
    "92252": {
        "state": "CA",
        "county": "San Bernardino County",
        "city": None,
    },
}


def _normalize_postal_code(postal_code: str | None) -> str | None:
    if not postal_code:
        return None

    stripped = postal_code.strip()
    if not stripped:
        return None

    digits = "".join(ch for ch in stripped if ch.isdigit())
    if len(digits) == 5:
        return digits

    return stripped.upper()


def resolve_by_zip(postal_code: str | None) -> dict[str, str | None]:
    """Resolve jurisdiction metadata for a postal code.

    Parameters
    ----------
    postal_code:
        The postal code (ZIP) provided by the client.

    Returns
    -------
    dict
        A dictionary with ``state``, ``county``, and ``city`` keys mapped to
        resolved values for supported pilot ZIP codes. When the postal code is
        unknown the values default to ``None``.
    """

    normalized = _normalize_postal_code(postal_code)
    if not normalized:
        return {"state": None, "county": None, "city": None}

    resolved = _KNOWN_ZIP_CODES.get(normalized)
    if not resolved:
        return {"state": None, "county": None, "city": None}

    return {
        "state": resolved.get("state"),
        "county": resolved.get("county"),
        "city": resolved.get("city"),
    }


__all__ = ["resolve_by_zip"]
