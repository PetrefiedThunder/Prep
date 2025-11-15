"""Compatibility package for shared operational modules."""

from .observability import DEFAULT_TARGETED_ROUTES, configure_fastapi_tracing

__all__ = ["DEFAULT_TARGETED_ROUTES", "configure_fastapi_tracing"]
