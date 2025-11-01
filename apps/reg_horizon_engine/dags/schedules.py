"""Airflow/Dagster compatible schedule definitions for the RHE."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class JobSchedule:
    """Lightweight representation of a recurring job schedule."""

    name: str
    interval: timedelta
    description: str


DEFAULT_SCHEDULES = [
    JobSchedule(
        name="verify_sources",
        interval=timedelta(days=7),
        description="Re-checks discovery sources for availability and accuracy.",
    ),
    JobSchedule(
        name="parse_documents",
        interval=timedelta(days=1),
        description="Fetches and parses newly published legislative documents.",
    ),
    JobSchedule(
        name="retrain_models",
        interval=timedelta(days=30),
        description="Retrains predictive models on the latest historical data.",
    ),
]
