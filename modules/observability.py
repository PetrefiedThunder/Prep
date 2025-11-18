"""Runtime tracing utilities for the Prep FastAPI gateway."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable

from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)

# Health check routes are traced by default to ensure the gateway remains responsive.
DEFAULT_TARGETED_ROUTES: tuple[str, ...] = ("/healthz",)


def _should_trace(path: str, routes: tuple[str, ...]) -> bool:
    """Return ``True`` when *path* should be traced."""

    normalized = path.rstrip("/") or "/"
    for route in routes:
        candidate = route.rstrip("/") or "/"
        if normalized == candidate or normalized.startswith(f"{candidate}/"):
            return True
    return False


def configure_fastapi_tracing(
    app: FastAPI, *, targeted_routes: Iterable[str] | None = None
) -> None:
    """Attach lightweight tracing to ``app`` for latency diagnostics.

    The middleware records request latency for the provided *targeted_routes* and logs
    the measurement at ``DEBUG`` level. Duplicate configuration is automatically
    ignored so the middleware is registered at most once per application instance.
    """

    routes = tuple(targeted_routes or DEFAULT_TARGETED_ROUTES)
    if not routes:
        logger.debug("Tracing skipped: no targeted routes configured")
        return

    if getattr(app.state, "_prep_tracing_configured", False):
        logger.debug("Tracing middleware already configured; skipping re-registration")
        return

    @app.middleware("http")
    async def _trace_requests(request: Request, call_next):  # type: ignore[override]
        if not _should_trace(request.url.path, routes):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.debug(
            "Traced request latency",
            extra={
                "path": request.url.path,
                "method": request.method,
                "elapsed_ms": round(elapsed_ms, 3),
            },
        )
        return response

    app.state._prep_tracing_configured = True

    logger.info("Tracing middleware configured", targeted_routes=list(routes))


__all__ = ["DEFAULT_TARGETED_ROUTES", "configure_fastapi_tracing"]
