#!/usr/bin/env python3
"""
Stripe Reconciliation Job (V60)
Validates Stripe charges vs internal bookings and exports mismatches
Usage: python scripts/reconcile_stripe.py [--month YYYY-MM]
"""

import csv
import os
import sys
from datetime import datetime, timedelta

import psycopg2
import stripe
from psycopg2.extras import RealDictCursor

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def get_stripe_charges(start_date, end_date):
    """Fetch all Stripe charges in date range"""
    charges = []
    has_more = True
    starting_after = None

    while has_more:
        params = {
            "limit": 100,
            "created": {"gte": int(start_date.timestamp()), "lte": int(end_date.timestamp())},
        }

        if starting_after:
            params["starting_after"] = starting_after

        response = stripe.Charge.list(**params)

        charges.extend(response.data)
        has_more = response.has_more
        if has_more:
            starting_after = response.data[-1].id

    return charges


def get_db_bookings(conn, start_date, end_date):
    """Fetch all bookings with payments in date range"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT
            booking_id,
            payment_intent_id,
            amount_cents,
            status,
            created_at
        FROM bookings
        WHERE created_at >= %s
          AND created_at <= %s
          AND payment_intent_id IS NOT NULL
        ORDER BY created_at
    """,
        (start_date, end_date),
    )

    return cursor.fetchall()


def reconcile(year_month=None):
    """Reconcile Stripe charges with database bookings"""

    # Determine date range
    if year_month:
        start_date = datetime.strptime(year_month, "%Y-%m")
        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1)
    else:
        # Default: last month
        today = datetime.now()
        start_date = datetime(today.year, today.month, 1) - timedelta(days=1)
        start_date = datetime(start_date.year, start_date.month, 1)
        end_date = datetime(today.year, today.month, 1)

    print(f"Reconciling from {start_date.date()} to {end_date.date()}")

    # Fetch Stripe charges
    print("Fetching Stripe charges...")
    stripe_charges = get_stripe_charges(start_date, end_date)
    print(f"  Found {len(stripe_charges)} Stripe charges")

    # Fetch DB bookings
    print("Fetching database bookings...")
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    db_bookings = get_db_bookings(conn, start_date, end_date)
    print(f"  Found {len(db_bookings)} database bookings")

    # Create lookup maps
    stripe_by_pi = {c.payment_intent: c for c in stripe_charges if c.payment_intent}
    db_by_pi = {b["payment_intent_id"]: b for b in db_bookings}

    # Find mismatches
    mismatches = []

    # Charges in Stripe but not in DB
    for pi_id, charge in stripe_by_pi.items():
        if pi_id not in db_by_pi:
            mismatches.append(
                {
                    "type": "stripe_only",
                    "payment_intent_id": pi_id,
                    "amount": charge.amount,
                    "stripe_created": datetime.fromtimestamp(charge.created),
                    "booking_id": None,
                    "db_amount": None,
                }
            )

    # Charges in DB but not in Stripe
    for pi_id, booking in db_by_pi.items():
        if pi_id not in stripe_by_pi:
            mismatches.append(
                {
                    "type": "db_only",
                    "payment_intent_id": pi_id,
                    "amount": None,
                    "stripe_created": None,
                    "booking_id": booking["booking_id"],
                    "db_amount": booking["amount_cents"],
                }
            )

    # Amount mismatches
    for pi_id in set(stripe_by_pi.keys()) & set(db_by_pi.keys()):
        stripe_amount = stripe_by_pi[pi_id].amount
        db_amount = db_by_pi[pi_id]["amount_cents"]

        if stripe_amount != db_amount:
            mismatches.append(
                {
                    "type": "amount_mismatch",
                    "payment_intent_id": pi_id,
                    "amount": stripe_amount,
                    "stripe_created": datetime.fromtimestamp(stripe_by_pi[pi_id].created),
                    "booking_id": db_by_pi[pi_id]["booking_id"],
                    "db_amount": db_amount,
                }
            )

    # Export to CSV
    if mismatches:
        filename = f"stripe_reconciliation_{start_date.strftime('%Y-%m')}.csv"

        with open(filename, "w", newline="") as csvfile:
            fieldnames = [
                "type",
                "payment_intent_id",
                "booking_id",
                "stripe_amount",
                "db_amount",
                "stripe_created",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for m in mismatches:
                writer.writerow(
                    {
                        "type": m["type"],
                        "payment_intent_id": m["payment_intent_id"],
                        "booking_id": m["booking_id"] or "N/A",
                        "stripe_amount": f"${m['amount'] / 100:.2f}" if m["amount"] else "N/A",
                        "db_amount": f"${m['db_amount'] / 100:.2f}" if m["db_amount"] else "N/A",
                        "stripe_created": m["stripe_created"] or "N/A",
                    }
                )

        print(f"\n❌ Found {len(mismatches)} mismatches!")
        print(f"   Exported to: {filename}")

    else:
        print("\n✓ No mismatches found! Everything reconciles correctly.")

    conn.close()


if __name__ == "__main__":
    year_month = sys.argv[1] if len(sys.argv) > 1 else None
    reconcile(year_month)
