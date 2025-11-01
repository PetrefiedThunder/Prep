"""LKG persistence helpers."""
from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Select, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..parser import Relationship
from ..store.models import lkg_edges, lkg_nodes


async def _get_or_create_node(session: AsyncSession, eli: str) -> int:
    query: Select[tuple[int]] = select(lkg_nodes.c.id).where(lkg_nodes.c.key == eli)
    result = await session.execute(query)
    node_id = result.scalar_one_or_none()
    if node_id is not None:
        return node_id

    await session.execute(
        insert(lkg_nodes).values(
            kind="document",
            key=eli,
            label=eli.split("/")[-1],
        )
    )
    result = await session.execute(query)
    node_id = result.scalar_one()
    return node_id


async def persist_relationships(session: AsyncSession, relationships: Iterable[Relationship]) -> None:
    """Persist extracted relationships into the lightweight knowledge graph."""

    for relationship in relationships:
        src_id = await _get_or_create_node(session, relationship.src_eli)
        dst_id = await _get_or_create_node(session, relationship.dst_eli)

        edge_query: Select[tuple[int]] = select(lkg_edges.c.id).where(
            lkg_edges.c.src == src_id,
            lkg_edges.c.dst == dst_id,
            lkg_edges.c.rel == relationship.rel.value,
        )
        existing = await session.execute(edge_query)
        if existing.scalar_one_or_none() is not None:
            continue

        await session.execute(
            insert(lkg_edges).values(
                src=src_id,
                dst=dst_id,
                rel=relationship.rel.value,
                snippet=relationship.snippet,
                confidence=relationship.confidence,
            )
        )
    await session.commit()


__all__ = ["persist_relationships"]
