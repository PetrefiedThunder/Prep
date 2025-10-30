"""Prometheus metrics helpers for the Prep platform."""

from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_LATENCY = Histogram(
    "prep_api_request_latency_seconds",
    "Latency of Prep API requests in seconds.",
    labelnames=("app", "method", "path", "status"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
)
REQUEST_COUNT = Counter(
    "prep_api_request_total",
    "Total number of Prep API requests processed.",
    labelnames=("app", "method", "path", "status"),
)
INTEGRATION_SYNC_FAILURES = Counter(
    "prep_integration_sync_failures_total",
    "Total integration sync failures encountered by the platform.",
    labelnames=("integration",),
)
INTEGRATION_SYNC_SUCCESS = Counter(
    "prep_integration_sync_success_total",
    "Total successful integration sync operations.",
    labelnames=("integration",),
)
DELIVERY_KITCHENS_GAUGE = Gauge(
    "prep_active_delivery_kitchens",
    "Number of delivery-only kitchens currently tracked.",
)
DELIVERIES_COUNTER = Counter(
    "prep_deliveries_total",
    "Total delivery bookings created across the platform.",
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record basic Prometheus metrics for every HTTP request."""

    def __init__(self, app, *, app_name: str = "prep-api") -> None:  # type: ignore[override]
        super().__init__(app)
        self._app_name = app_name

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        start = time.perf_counter()
        path_template = _resolve_path_template(request)
        labels: Dict[str, Any] = {
            "app": self._app_name,
            "method": request.method,
            "path": path_template,
            "status": "500",
        }
        try:
            response = await call_next(request)
        except Exception:
            duration = time.perf_counter() - start
            REQUEST_LATENCY.labels(**labels).observe(duration)
            REQUEST_COUNT.labels(**labels).inc()
            raise
        else:
            duration = time.perf_counter() - start
            labels["status"] = str(getattr(response, "status_code", 500))
            REQUEST_LATENCY.labels(**labels).observe(duration)
            REQUEST_COUNT.labels(**labels).inc()
            return response


def create_metrics_router() -> APIRouter:
    """Return an APIRouter exposing the `/metrics` endpoint."""

    router = APIRouter()

    @router.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    return router


def _resolve_path_template(request: Request) -> str:
    route = request.scope.get("route")
    if route is None:
        return request.url.path
    return getattr(route, "path", request.url.path)


__all__ = [
    "INTEGRATION_SYNC_FAILURES",
    "INTEGRATION_SYNC_SUCCESS",
    "DELIVERY_KITCHENS_GAUGE",
    "DELIVERIES_COUNTER",
    "MetricsMiddleware",
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "create_metrics_router",
]
