"""Simplified AKN repository abstraction."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AKNRepo:
    """Placeholder repository for retrieving stored Akoma Ntoso documents."""

    def get_xml(self, eli: str) -> bytes:
        """Return raw Akoma Ntoso XML for the given ELI.

        This stub implementation raises ``NotImplementedError`` so that callers
        can provide an actual persistence layer without modifying the API.
        """

        raise NotImplementedError(f"AKNRepo.get_xml not implemented for {eli}")
