"""Prometheus metric definitions for the SF regulatory service."""

from __future__ import annotations

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover - used in offline test environments
    CONTENT_TYPE_LATEST = "text/plain"

    def generate_latest() -> bytes:  # type: ignore[override]
        return b""

    class _NoopMetric:
        def __init__(self, *args, **kwargs):  # noqa: D401 - noop constructor
            pass

        def labels(self, *args, **kwargs):  # noqa: D401 - metric interface
            return self

        def inc(self, amount: float = 1.0) -> None:  # noqa: D401 - metric interface
            return None

        def observe(self, value: float) -> None:  # noqa: D401 - metric interface
            return None

        def set(self, value: float) -> None:  # noqa: D401 - metric interface
            return None

    class Counter(_NoopMetric):  # type: ignore[misc]
        pass

    class Gauge(_NoopMetric):  # type: ignore[misc]
        pass

    class Histogram(_NoopMetric):  # type: ignore[misc]
        pass

    PROMETHEUS_AVAILABLE = False

sf_permit_validations_total = Counter(
    "sf_permit_validations_total",
    "Total health permit validations",
    labelnames=("result",),
)

sf_zoning_checks_total = Counter(
    "sf_zoning_checks_total",
    "Total zoning checks",
    labelnames=("outcome",),
)

sf_compliance_check_total = Counter(
    "sf_compliance_check_total",
    "Composite compliance decisions",
    labelnames=("status",),
)

sf_tax_lines_total = Counter(
    "sf_tax_lines_total",
    "San Francisco tax lines generated",
    labelnames=("jurisdiction",),
)

sf_etl_runs_total = Counter(
    "sf_etl_runs_total",
    "Nightly ETL runs recorded",
    labelnames=("status",),
)

http_server_latency_seconds = Histogram(
    "http_server_latency_seconds",
    "HTTP latency for SF regulatory endpoints",
    labelnames=("route",),
)

sf_hosts_compliant_ratio = Gauge(
    "sf_hosts_compliant_ratio",
    "Ratio of SF hosts in compliant status",
)
