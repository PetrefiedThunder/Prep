"""Shared helpers for city-focused API routes."""
from __future__ import annotations

from functools import lru_cache
from importlib import import_module

_CANON = {
    "san francisco": "san_francisco",
    "sf": "san_francisco",
    "oakland": "oakland",
    "berkeley": "berkeley",
    "san jose": "san_jose",
    "sj": "san_jose",
    "palo alto": "palo_alto",
    "palo_alto": "palo_alto",
    "joshua tree": "joshua_tree",
    "joshua_tree": "joshua_tree",
}

_MOD_MAP = {
    "san_francisco": "data.ingestors.sf_dph",
    "oakland": "data.ingestors.oakland_dph",
    "berkeley": "data.ingestors.berkeley_dph",
    "san_jose": "data.ingestors.san_jose_dph",
    "palo_alto": "data.ingestors.palo_alto_dph",
    "joshua_tree": "data.ingestors.joshua_tree_dph",
}

SUPPORTED_CITIES: tuple[str, ...] = tuple(sorted(_MOD_MAP.keys()))


def normalize_city(city: str) -> str:
    """Normalize a city string to the canonical identifier used by data modules."""

    key = city.strip().lower().replace("-", "_")
    normalized = _CANON.get(key, key.replace(" ", "_"))
    if normalized not in _MOD_MAP:
        raise KeyError(city)
    return normalized


@lru_cache(maxsize=64)
def ingestor_module_for(city_norm: str):
    """Return the ingestion module for a normalized city name."""

    path = _MOD_MAP.get(city_norm)
    if not path:
        raise KeyError(city_norm)
    return import_module(path)


__all__ = ["SUPPORTED_CITIES", "normalize_city", "ingestor_module_for"]
