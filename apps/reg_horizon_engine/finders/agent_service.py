"""Finder agent orchestration for discovering regulatory sources."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, HttpUrl

from ..config import get_settings


class PortalCandidate(BaseModel):
    """Normalized representation of a discovered portal candidate."""

    municipality_id: str
    source_type: str
    source_url: HttpUrl
    confidence: float


@dataclass
class FinderAgent:
    """Simple abstraction around an LLM-planned discovery workflow."""

    search_backends: Sequence[str]

    async def discover(self, municipality_id: str, topic: str) -> list[PortalCandidate]:
        """Return ranked discovery candidates.

        This method is intentionally stubbed and should be backed by an
        orchestrated agent that leverages configured search providers and
        prompt templates.
        """

        _ = (topic,)
        settings = get_settings()
        default_confidence = settings.default_source_confidence
        base_url = f"https://{municipality_id}.example.gov/ordinances"
        return [
            PortalCandidate(
                municipality_id=municipality_id,
                source_type="agenda",
                source_url=base_url,
                confidence=default_confidence,
            )
        ]

    async def verify(self, candidates: Iterable[PortalCandidate]) -> list[PortalCandidate]:
        """Placeholder verification hook returning annotated candidates."""

        verified = []
        for candidate in candidates:
            verified.append(
                candidate.copy(
                    update={
                        "confidence": min(candidate.confidence + 0.1, 1.0),
                    }
                )
            )
        return verified


async def record_candidates(
    session, candidates: Sequence[PortalCandidate]
) -> list[dict[str, str]]:
    """Persist discovered candidates into the database.

    The session parameter is intentionally untyped to avoid importing
    SQLAlchemy within this module, keeping the agent layer decoupled.
    """

    now = datetime.now(datetime.UTC)
    rows = []
    for candidate in candidates:
        rows.append(
            {
                "municipality_id": candidate.municipality_id,
                "source_type": candidate.source_type,
                "source_url": str(candidate.source_url),
                "confidence": candidate.confidence,
                "last_verified": now,
            }
        )
    if hasattr(session, "execute"):
        from sqlalchemy import insert

        from ..models import RHESource

        await session.execute(insert(RHESource).values(rows))
    return rows
