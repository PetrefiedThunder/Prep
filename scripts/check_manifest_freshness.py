"""Verify the regulation manifest has been refreshed recently."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

import psycopg


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--max_age_hours", type=int, default=48)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    with psycopg.connect(args.db) as conn, conn.cursor() as cur:
        cur.execute("SELECT max(effective_date) FROM regulation_manifest")
        row = cur.fetchone()

    if not row or not row[0]:
        print("No effective_date in manifest")
        return 1

    latest = row[0]
    if isinstance(latest, str):
        latest = datetime.fromisoformat(latest)

    latest = latest.replace(tzinfo=timezone.utc) if latest.tzinfo is None else latest.astimezone(timezone.utc)
    age = datetime.now(timezone.utc) - latest
    print("Latest manifest:", latest.isoformat(), "age_hours=", age.total_seconds() / 3600)
    return 0 if age <= timedelta(hours=args.max_age_hours) else 2


if __name__ == "__main__":
    sys.exit(main())
