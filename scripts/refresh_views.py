"""Refresh materialized views used by Prep analytics."""

from __future__ import annotations

import asyncio
import os

import asyncpg


async def refresh_mv_host_metrics() -> None:
    """Refresh the mv_host_metrics materialized view concurrently."""

    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        database=os.getenv("DB_NAME", "prepchef"),
    )

    try:
        await conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_host_metrics;")
    finally:
        await conn.close()

    print("mv_host_metrics refreshed successfully!")


if __name__ == "__main__":
    asyncio.run(refresh_mv_host_metrics())
