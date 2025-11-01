"""European Legislation Identifier helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class ELI:
    """Minimal representation of an ELI identifier."""

    jurisdiction: str
    date: str | date
    doc_type: str
    natural_id: str

    def iri(self) -> str:
        if isinstance(self.date, date):
            date_str = self.date.isoformat()
        else:
            date_str = self.date
        return f"/eli/{self.jurisdiction}/{date_str}/{self.doc_type}/{self.natural_id}".rstrip("/")


__all__ = ["ELI"]
