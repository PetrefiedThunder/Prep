"""Optional Neo4j adapter for the knowledge graph."""
from __future__ import annotations

from dataclasses import dataclass

from neo4j import GraphDatabase


@dataclass
class Neo4jLKG:
    """Thin wrapper around a Neo4j driver for persisting relationships."""

    uri: str
    user: str
    password: str

    def __post_init__(self) -> None:
        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self) -> None:
        self._driver.close()

    def create_rel(self, src_eli: str, dst_eli: str, rel: str) -> None:
        query = f"""
        MERGE (s:Doc {{eli: $src}})
        MERGE (d:Doc {{eli: $dst}})
        MERGE (s)-[r:{rel.upper()}]->(d)
        SET r.created_at = coalesce(r.created_at, datetime())
        """
        with self._driver.session() as session:
            session.run(query, src=src_eli, dst=dst_eli)


__all__ = ["Neo4jLKG"]
