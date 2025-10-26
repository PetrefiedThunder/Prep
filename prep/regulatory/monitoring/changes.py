"""Utilities for monitoring and detecting regulatory changes over time."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from difflib import Differ
from typing import Dict, Iterable, List, Optional, Sequence


@dataclass(slots=True)
class Change:
    """Represents a detected change in a regulation artifact."""

    regulation_id: Optional[str]
    change_type: str
    old_text: str
    new_text: str
    timestamp: datetime
    diff: Optional[List[str]] = None


class RegulatoryChangeDetector:
    """Detect changes between versions of regulation collections."""

    def __init__(self) -> None:
        self.previous_versions: Dict[str, tuple[str, Sequence[Dict[str, str]]]] = {}

    async def detect_changes(self, new_regulations: Sequence[Dict[str, str]], jurisdiction: str) -> List[Change]:
        """Detect changes between previously stored regulations and the provided list."""

        current_hash = self.hash_regulations(new_regulations)
        changes: List[Change] = []
        if jurisdiction in self.previous_versions:
            old_hash, old_regulations = self.previous_versions[jurisdiction]
            if current_hash != old_hash:
                changes = self.compare_regulations(old_regulations, new_regulations)
        self.previous_versions[jurisdiction] = (current_hash, new_regulations)
        return changes

    def compare_regulations(
        self, old: Sequence[Dict[str, str]], new: Sequence[Dict[str, str]]
    ) -> List[Change]:
        """Compare regulation sequences and return detected textual changes."""

        differ = Differ()
        changes: List[Change] = []
        for index, (old_reg, new_reg) in enumerate(zip(old, new)):
            old_text = old_reg.get("text", "")
            new_text = new_reg.get("text", "")
            diff = list(differ.compare(old_text.split(), new_text.split()))
            if any(line.startswith("+ ") or line.startswith("- ") for line in diff):
                changes.append(
                    Change(
                        regulation_id=new_reg.get("id") or old_reg.get("id") or str(index),
                        change_type="text_change",
                        old_text=old_text,
                        new_text=new_text,
                        timestamp=datetime.utcnow(),
                        diff=diff,
                    )
                )
        if len(new) > len(old):
            for new_reg in new[len(old) :]:
                changes.append(
                    Change(
                        regulation_id=new_reg.get("id"),
                        change_type="added",
                        old_text="",
                        new_text=new_reg.get("text", ""),
                        timestamp=datetime.utcnow(),
                        diff=None,
                    )
                )
        elif len(old) > len(new):
            for old_reg in old[len(new) :]:
                changes.append(
                    Change(
                        regulation_id=old_reg.get("id"),
                        change_type="removed",
                        old_text=old_reg.get("text", ""),
                        new_text="",
                        timestamp=datetime.utcnow(),
                        diff=None,
                    )
                )
        return changes

    def hash_regulations(self, regulations: Iterable[Dict[str, str]]) -> str:
        """Generate a stable hash for a collection of regulations."""

        digest = hashlib.sha256()
        for regulation in regulations:
            digest.update((regulation.get("id", "")).encode("utf-8"))
            digest.update((regulation.get("text", "")).encode("utf-8"))
            digest.update((regulation.get("jurisdiction", "")).encode("utf-8"))
        return digest.hexdigest()


__all__ = ["Change", "RegulatoryChangeDetector"]
