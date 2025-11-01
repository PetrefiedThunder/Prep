"""Prometheus metrics used by the City ETL orchestrator."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

try:  # pragma: no cover - import guard for offline environments
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover - used in unit tests without prometheus installed
    CONTENT_TYPE_LATEST = "text/plain"

    def generate_latest() -> bytes:  # type: ignore[override]
        return b""

    class _NoopMetric:
        def __init__(self, *args, **kwargs):  # noqa: D401 - mimic prometheus interface
            pass

        def labels(self, *args, **kwargs):  # noqa: D401 - mimic prometheus interface
            return self

        def inc(self, amount: float = 1.0) -> None:  # noqa: D401
            return None

        def observe(self, value: float) -> None:  # noqa: D401
            return None

        def set(self, value: float) -> None:  # noqa: D401
            return None

    class Counter(_NoopMetric):  # type: ignore[misc]
        pass

    class Gauge(_NoopMetric):  # type: ignore[misc]
        pass

    class Histogram(_NoopMetric):  # type: ignore[misc]
        pass

    PROMETHEUS_AVAILABLE = False

city_etl_runs_total = Counter(
    "city_etl_runs_total",
    "Total orchestrated ETL executions",
    labelnames=("city", "status"),
)

city_etl_last_run_timestamp = Gauge(
    "city_etl_last_run_timestamp",
    "Unix timestamp of the most recent orchestrated ETL run",
    labelnames=("city",),
)

city_etl_last_success_timestamp = Gauge(
    "city_etl_last_success_timestamp",
    "Unix timestamp of the most recent successful ETL run",
    labelnames=("city",),
)

city_etl_freshness_seconds = Gauge(
    "city_etl_freshness_seconds",
    "Age in seconds of the freshest successful ETL run",
    labelnames=("city",),
)

city_etl_run_duration_seconds = Histogram(
    "city_etl_run_duration_seconds",
    "Duration of orchestrated ETL runs in seconds",
    labelnames=("city",),
)


def update_freshness_gauge(city: str, last_success_at: Optional[datetime]) -> None:
    """Update the freshness gauge based on the latest success timestamp."""

    if last_success_at is None:
        # A NaN value allows Prometheus alert rules to detect missing data.
        city_etl_freshness_seconds.labels(city=city).set(float("nan"))
        return

    age_seconds = max(0.0, (datetime.utcnow() - last_success_at).total_seconds())
    city_etl_freshness_seconds.labels(city=city).set(age_seconds)
