"""Gazette discovery helpers integrating semantic filtering."""
from __future__ import annotations

from collections.abc import Iterable

from reg_horizon_engine.semantic import keep_relevant


def _deduplicate(candidates: Iterable[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for candidate in candidates:
        key = candidate.get("url") or candidate.get("href") or candidate.get("title")
        if key and key not in seen:
            seen[key] = dict(candidate)
    return list(seen.values())


def select_relevant_links(candidates: Iterable[dict], threshold: float = 0.45) -> list[dict]:
    """Return the top semantically-relevant gazette links."""

    uniq = _deduplicate(candidates)
    links = keep_relevant(uniq, threshold=threshold)
    return links[:100]


__all__ = ["select_relevant_links"]
