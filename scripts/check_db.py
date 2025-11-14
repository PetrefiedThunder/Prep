#!/usr/bin/env python3
"""Database health check script.

Validates DATABASE_URL is set and database is reachable.
Use this before running migrations or starting services.

Exit codes:
  0 - Database is healthy and reachable
  1 - DATABASE_URL not set or database connection failed
"""

import os
import sys
from typing import NoReturn


def fail(message: str) -> NoReturn:
    """Print error message and exit with code 1."""
    print(f"❌ Database check failed: {message}", file=sys.stderr)
    sys.exit(1)


def check_database() -> None:
    """Check database connectivity and fail fast with clear errors."""
    # Check DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        fail(
            "DATABASE_URL environment variable not set.\n"
            "   Fix: Copy .env.example to .env.local and set DATABASE_URL, then:\n"
            "        export $(cat .env.local | xargs)"
        )

    print(f"✓ DATABASE_URL is set: {database_url.split('@')[0]}@***")

    # Try to connect
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.pool import NullPool
    except ImportError as e:
        fail(f"SQLAlchemy not installed: {e}\n   Fix: pip install sqlalchemy")

    try:
        # Use NullPool to avoid connection pooling for health check
        engine = create_engine(database_url, poolclass=NullPool)

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(__import__("sqlalchemy").text("SELECT 1")).scalar()
            if result != 1:
                fail("Database query returned unexpected result")

        print("✓ Database connection successful")

        # Check if tables exist (optional, non-fatal)
        with engine.connect() as conn:
            inspector = __import__("sqlalchemy").inspect(engine)
            tables = inspector.get_table_names()
            if tables:
                print(f"✓ Found {len(tables)} tables in database")
            else:
                print("⚠ Warning: No tables found. Run 'make migrate' to initialize schema.")

        print("\n✅ Database health check passed")

    except Exception as e:
        error_msg = str(e)

        # Provide helpful error messages based on common issues
        if "could not connect to server" in error_msg.lower():
            fail(
                f"Cannot connect to database server: {error_msg}\n"
                "   Fix: Ensure PostgreSQL is running:\n"
                "        docker compose up -d postgres\n"
                "        OR make up"
            )
        elif "does not exist" in error_msg.lower():
            fail(
                f"Database does not exist: {error_msg}\n"
                "   Fix: Create the database or let docker-compose create it:\n"
                "        make up"
            )
        elif "authentication failed" in error_msg.lower():
            fail(
                f"Database authentication failed: {error_msg}\n"
                "   Fix: Check username/password in DATABASE_URL match your PostgreSQL config"
            )
        else:
            fail(f"Database connection error: {error_msg}")


if __name__ == "__main__":
    check_database()
