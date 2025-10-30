"""Observability utilities for cross-cutting instrumentation."""

from .tracing import (
    DEFAULT_TARGETED_ROUTES,
    configure_fastapi_tracing,
    get_tracer,
)

__all__ = [
    "configure_fastapi_tracing",
    "DEFAULT_TARGETED_ROUTES",
    "get_tracer",
]
