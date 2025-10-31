"""Lightweight OpenTelemetry helpers for the city regulatory service."""

from __future__ import annotations

from functools import lru_cache
import logging
from typing import Any

try:  # pragma: no cover - optional dependency
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
except Exception:  # pragma: no cover - graceful fallback when OTel is unavailable
    trace = None  # type: ignore[assignment]
    TracerProvider = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class _NullSpan:  # pragma: no cover - trivial container
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def __getattr__(self, _: str) -> Any:
        return lambda *args, **kwargs: None


class _NullTracer:  # pragma: no cover - trivial container
    def start_as_current_span(self, *_args: Any, **_kwargs: Any) -> _NullSpan:
        return _NullSpan()


@lru_cache(maxsize=1)
def get_tracer() -> Any:
    """Return a configured tracer or a no-op stand-in when unavailable."""

    if trace is None or TracerProvider is None:
        logger.debug("OpenTelemetry not installed; returning noop tracer")
        return _NullTracer()

    provider = trace.get_tracer_provider()
    if provider.__class__.__name__ == "DefaultTracerProvider":
        resource = Resource.create({"service.name": "city-regulatory-service"})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
    return trace.get_tracer("apps.city_regulatory_service")


__all__ = ["get_tracer"]
