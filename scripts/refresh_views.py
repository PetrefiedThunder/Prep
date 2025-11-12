"""Refresh materialized views used by Prep analytics."""

from __future__ import annotations

import argparse
import asyncio
import os
from typing import Any

import asyncpg


async def refresh_mv_host_metrics(**connect_kwargs: Any) -> None:
    """Refresh the mv_host_metrics materialized view concurrently."""

    dsn = connect_kwargs.pop("dsn", None)
    if dsn:
        conn = await asyncpg.connect(dsn=dsn)
    else:
        conn = await asyncpg.connect(
            host=connect_kwargs.get("host") or os.getenv("DB_HOST", "localhost"),
            port=int(connect_kwargs.get("port") or os.getenv("DB_PORT", 5432)),
            user=connect_kwargs.get("user") or os.getenv("DB_USER", "postgres"),
            password=connect_kwargs.get("password") or os.getenv("DB_PASSWORD", "postgres"),
            database=connect_kwargs.get("database") or os.getenv("DB_NAME", "prepchef"),
        )

    try:
        await conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_host_metrics;")
    finally:
        await conn.close()

    print("mv_host_metrics refreshed successfully!")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh the mv_host_metrics materialized view concurrently.",
    )
    parser.add_argument(
        "--dsn",
        help="Optional PostgreSQL DSN. Overrides individual host/port/user options when provided.",
    )
    parser.add_argument("--host", help="Database host. Defaults to $DB_HOST or localhost.")
    parser.add_argument(
        "--port",
        type=int,
        help="Database port. Defaults to $DB_PORT or 5432.",
    )
    parser.add_argument("--user", help="Database user. Defaults to $DB_USER or postgres.")
    parser.add_argument(
        "--password", help="Database password. Defaults to $DB_PASSWORD or postgres."
    )
    parser.add_argument(
        "--database",
        help="Database name. Defaults to $DB_NAME or prepchef.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    kwargs = {k: v for k, v in vars(args).items() if v is not None}
    asyncio.run(refresh_mv_host_metrics(**kwargs))


if __name__ == "__main__":
    main()
