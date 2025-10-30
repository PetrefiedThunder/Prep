"""Observability utilities for the Prep platform."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Mapping

if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from ..core.orchestration import ComplianceDomain


@dataclass
class Span:
    name: str
    tags: Dict[str, Any]

    async def __aenter__(self) -> "Span":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None

    def set_tag(self, key: str, value: Any) -> None:
        self.tags[key] = value


class DistributedTracer:
    """Minimal async tracer implementation."""

    @asynccontextmanager
    async def start_span(self, name: str):
        span = Span(name=name, tags={})
        try:
            yield span
        finally:
            pass


class MetricsCollector:
    """Collects numeric metrics for compliance workflows."""

    def __init__(self) -> None:
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + value

    def counters(self) -> Dict[str, int]:
        return dict(self._counters)

    def set_gauge(self, name: str, value: float | int) -> None:
        self._gauges[name] = float(value)

    def gauges(self) -> Dict[str, float]:
        return dict(self._gauges)


class StructuredLogger:
    """Structured logging helper."""

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []

    def info(self, message: str, **context: Any) -> None:
        entry = {"level": "INFO", "message": message, **context}
        self._entries.append(entry)

    def entries(self) -> List[Dict[str, Any]]:
        return list(self._entries)


class EnterpriseObservability:
    """End-to-end observability stack wrapper."""

    def __init__(self) -> None:
        self.metrics = MetricsCollector()
        self.logging = StructuredLogger()
        self.tracing = DistributedTracer()

    def record_job_result(
        self,
        job_name: str,
        *,
        success: bool,
        duration_seconds: float,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Capture success/failure metrics for background jobs."""

        status = "success" if success else "failure"
        self.metrics.increment(f"jobs.{job_name}.{status}")
        self.metrics.set_gauge(f"jobs.{job_name}.last_duration_seconds", duration_seconds)
        log_payload = {"job_name": job_name, "status": status, "duration_seconds": duration_seconds}
        if metadata:
            log_payload.update(metadata)
        self.logging.info("Background job completed", **log_payload)

    async def track_compliance_workflow(
        self, workflow_id: str, domains: Iterable["ComplianceDomain"]
    ) -> None:
        """End-to-end compliance workflow monitoring."""

        async with self.tracing.start_span(f"compliance_workflow_{workflow_id}") as span:
            span.set_tag("domains", [d.value for d in domains])
            self.metrics.increment("compliance_workflows.started")
            self.logging.info(
                "Compliance workflow started",
                workflow_id=workflow_id,
                domains=[domain.value for domain in domains],
            )


__all__ = [
    "EnterpriseObservability",
    "DistributedTracer",
    "MetricsCollector",
    "StructuredLogger",
]
