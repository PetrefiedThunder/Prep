"""Lightweight request tracing for high-value Prep APIs."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, MutableMapping, Sequence

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

DEFAULT_TARGETED_ROUTES: Sequence[str] = (
    "/api/v1/platform/users/register",
    "/api/v1/platform/auth/login",
    "/api/v1/platform/bookings",
    "/api/v1/platform/payments/intent",
    "/healthz",
)


@dataclass(frozen=True)
class SpanEvent:
    """Immutable payload describing a completed request span."""

    name: str
    start_time_ms: float
    duration_ms: float
    attributes: Dict[str, Any] = field(default_factory=dict)


class SpanExporter:
    """Interface for exporting finished spans."""

    def export(self, span: SpanEvent) -> None:  # pragma: no cover - interface contract
        raise NotImplementedError


class LoggingSpanExporter(SpanExporter):
    """Exporter that writes span metadata to the structured logger."""

    def export(self, span: SpanEvent) -> None:  # pragma: no cover - logging wrapper
        logger.info(
            "Tracing span completed",
            extra={
                "span_name": span.name,
                "duration_ms": f"{span.duration_ms:.2f}",
                "attributes": span.attributes,
            },
        )


class InMemorySpanExporter(SpanExporter):
    """Exporter useful for tests or local debugging."""

    def __init__(self) -> None:
        self._spans: List[SpanEvent] = []

    def export(self, span: SpanEvent) -> None:
        self._spans.append(span)

    def spans(self) -> List[SpanEvent]:
        return list(self._spans)


class Tracer:
    """Minimal tracer responsible for filtering and exporting spans."""

    def __init__(
        self,
        targeted_routes: Iterable[str],
        exporters: Iterable[SpanExporter] | None = None,
    ) -> None:
        self._targeted_routes = frozenset(targeted_routes)
        self._exporters = list(exporters or [LoggingSpanExporter()])

    # ------------------------------------------------------------------
    def should_trace(self, route: str | None) -> bool:
        return bool(route and (not self._targeted_routes or route in self._targeted_routes))

    @contextmanager
    def start_span(self, name: str, *, attributes: MutableMapping[str, Any] | None = None) -> Iterator["ActiveSpan"]:
        span = ActiveSpan(name=name, attributes=dict(attributes or {}), tracer=self)
        try:
            yield span
        except Exception as exc:
            span.set_attribute("error", True)
            span.set_attribute("error.type", exc.__class__.__name__)
            span.set_attribute("error.message", str(exc))
            raise
        finally:
            span.finish()

    def export(self, span: SpanEvent) -> None:
        for exporter in self._exporters:
            exporter.export(span)

    def update_targets(self, routes: Iterable[str]) -> None:
        self._targeted_routes = frozenset(routes)


@dataclass
class ActiveSpan:
    """Represents a span currently in-flight."""

    name: str
    attributes: Dict[str, Any]
    tracer: Tracer
    start_time: float = field(default_factory=time.perf_counter)

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def finish(self) -> None:
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        event = SpanEvent(
            name=self.name,
            start_time_ms=self.start_time * 1000,
            duration_ms=duration_ms,
            attributes=dict(self.attributes),
        )
        self.tracer.export(event)


class TracingMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that records spans for targeted routes."""

    def __init__(self, app: FastAPI, tracer: Tracer) -> None:
        super().__init__(app)
        self._tracer = tracer

    async def dispatch(self, request: Request, call_next) -> Response:
        route = request.scope.get("path")
        if not self._tracer.should_trace(route):
            return await call_next(request)

        attributes: Dict[str, Any] = {
            "http.method": request.method,
            "http.route": route,
        }

        with self._tracer.start_span(f"{request.method} {route}", attributes=attributes) as span:
            response: Response | None = None
            try:
                response = await call_next(request)
                span.set_attribute("http.status_code", response.status_code)
                return response
            finally:
                if response is None:
                    span.set_attribute("http.status_code", "error")


_tracer: Tracer | None = None


def configure_fastapi_tracing(
    app: FastAPI,
    *,
    service_name: str | None = None,
    targeted_routes: Sequence[str] | None = None,
) -> None:
    """Register tracing middleware for the provided FastAPI application."""

    del service_name  # The lightweight tracer does not currently use service names.

    routes = targeted_routes or DEFAULT_TARGETED_ROUTES
    global _tracer
    if _tracer is None:
        _tracer = Tracer(routes)
        logger.info("Initialized lightweight tracer", extra={"targeted_routes": list(routes)})
    else:
        _tracer.update_targets(routes)
        logger.info("Updated tracer targeted routes", extra={"targeted_routes": list(routes)})

    if not getattr(app.state, "_prep_tracing_instrumented", False):
        app.add_middleware(TracingMiddleware, tracer=_tracer)
        app.state._prep_tracing_instrumented = True
        logger.info("Tracing middleware attached to FastAPI app")


def get_tracer() -> Tracer:
    """Expose the shared tracer instance for custom instrumentation."""

    global _tracer
    if _tracer is None:
        _tracer = Tracer(DEFAULT_TARGETED_ROUTES)
        logger.warning(
            "Tracing configured lazily; consider calling configure_fastapi_tracing at startup"
        )
    return _tracer


__all__ = [
    "ActiveSpan",
    "DEFAULT_TARGETED_ROUTES",
    "InMemorySpanExporter",
    "LoggingSpanExporter",
    "SpanEvent",
    "SpanExporter",
    "TracingMiddleware",
    "configure_fastapi_tracing",
    "get_tracer",
]
