"""Diff helpers for normalized documents."""
from __future__ import annotations

from typing import Iterable

from .normalize import Paragraph


Change = dict[str, object]


def diff_paragraphs(old: Iterable[Paragraph], new: Iterable[Paragraph]) -> list[Change]:
    """Return a simple diff summary between two paragraph collections."""

    old_index = {para.hash: para for para in old}
    new_index = {para.hash: para for para in new}

    changes: list[Change] = []

    for para in new:
        if para.hash not in old_index:
            changes.append({"type": "added", "para_hash": para.hash, "new": para.model_dump()})
        else:
            old_para = old_index[para.hash]
            if para.text != old_para.text:
                changes.append(
                    {
                        "type": "modified",
                        "para_hash": para.hash,
                        "old": old_para.model_dump(),
                        "new": para.model_dump(),
                    }
                )

    for para in old:
        if para.hash not in new_index:
            changes.append({"type": "removed", "para_hash": para.hash, "old": para.model_dump()})

    return changes
