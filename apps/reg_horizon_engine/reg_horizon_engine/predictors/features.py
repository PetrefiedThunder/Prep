"""Feature engineering helpers for momentum models."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession


async def graph_stats_for_async(eli: str, session: AsyncSession) -> dict[str, int]:
    """Asynchronously compute basic knowledge graph statistics for an ELI."""

    cites = await session.execute(
        text(
            """
            select count(*) from lkg_edges e
            join lkg_nodes n on e.src = n.id
            where n.key = :eli and e.rel = 'cites'
            """
        ),
        {"eli": eli},
    )
    amends = await session.execute(
        text(
            """
            select count(*) from lkg_edges e
            join lkg_nodes n on e.src = n.id
            where n.key = :eli and e.rel = 'amends'
            """
        ),
        {"eli": eli},
    )
    indeg = await session.execute(
        text(
            """
            select count(*) from lkg_edges e
            join lkg_nodes n on e.dst = n.id
            where n.key = :eli
            """
        ),
        {"eli": eli},
    )
    return {
        "citations": int(cites.scalar_one()),
        "amends": int(amends.scalar_one()),
        "in_degree": int(indeg.scalar_one()),
    }


def graph_stats_for(eli: str, session: Connection) -> dict[str, int]:
    """Synchronously compute basic knowledge graph statistics for an ELI."""

    cites = session.execute(
        text(
            """
            select count(*) from lkg_edges e
            join lkg_nodes n on e.src = n.id
            where n.key = :eli and e.rel = 'cites'
            """
        ),
        {"eli": eli},
    )
    amends = session.execute(
        text(
            """
            select count(*) from lkg_edges e
            join lkg_nodes n on e.src = n.id
            where n.key = :eli and e.rel = 'amends'
            """
        ),
        {"eli": eli},
    )
    indeg = session.execute(
        text(
            """
            select count(*) from lkg_edges e
            join lkg_nodes n on e.dst = n.id
            where n.key = :eli
            """
        ),
        {"eli": eli},
    )
    return {
        "citations": int(cites.scalar_one()),
        "amends": int(amends.scalar_one()),
        "in_degree": int(indeg.scalar_one()),
    }


__all__ = ["graph_stats_for", "graph_stats_for_async"]
