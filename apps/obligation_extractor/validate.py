"""Symbolic validation helpers for obligation outputs."""
from __future__ import annotations

from typing import Any, Tuple


def assert_deontic_consistency(objs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition obligations into accepted and rejected lists.

    The implementation is intentionally conservative and only filters obvious
    conflicts between obligations and prohibitions with the same subject and
    action pair.
    """

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_pairs: dict[tuple[str, str], str] = {}

    for obj in objs:
        subject = obj.get("subject")
        action = obj.get("action")
        key = (subject or "", action or "")
        current_type = obj.get("type")

        if key in seen_pairs and {seen_pairs[key], current_type} == {"obligation", "prohibition"}:
            rejected.append({"object": obj, "reason": "conflicting deontic modal"})
            continue

        seen_pairs[key] = current_type
        accepted.append(obj)

    return accepted, rejected
