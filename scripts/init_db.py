"""Initialize the Prep database using the SQL migration script."""

from __future__ import annotations

import asyncio
import os

import asyncpg


async def init_database() -> None:
    """Execute the bootstrap SQL migration against PostgreSQL."""

    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        database=os.getenv("DB_NAME", "prepchef"),
    )

    try:
        with open("migrations/init.sql", encoding="utf-8") as sql_file:
            sql = sql_file.read()
        await conn.execute(sql)
    finally:
        await conn.close()

    print("Database initialized successfully!")


if __name__ == "__main__":
    asyncio.run(init_database())
