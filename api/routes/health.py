"""Comprehensive health check endpoints for production observability.

This module provides:
- /health - Full dependency health check (for monitoring)
- /ready - Kubernetes readiness probe (can serve traffic)
- /live - Kubernetes liveness probe (process is alive)

Health checks include:
- Database connectivity and query performance
- Redis connectivity and latency
- MinIO/S3 storage availability
- External service dependencies
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, Response, status

from prep.observability.logging_config import get_logger

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class DependencyHealth:
    """Health status of a single dependency."""

    name: str
    status: HealthStatus
    latency_ms: float | None = None
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Complete health check result."""

    status: HealthStatus
    timestamp: str
    version: str
    uptime_seconds: float
    dependencies: list[DependencyHealth]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "dependencies": [
                {
                    "name": dep.name,
                    "status": dep.status.value,
                    "latency_ms": round(dep.latency_ms, 2) if dep.latency_ms else None,
                    "message": dep.message,
                    **({"details": dep.details} if dep.details else {}),
                }
                for dep in self.dependencies
            ],
        }


# Track startup time for uptime calculation
_startup_time = time.time()


async def check_database_health() -> DependencyHealth:
    """Check PostgreSQL database connectivity and performance."""
    try:
        import asyncpg

        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            return DependencyHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message="DATABASE_URL not configured",
            )

        # Convert postgres:// to postgresql:// if needed
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        start = time.perf_counter()
        conn = await asyncio.wait_for(
            asyncpg.connect(database_url),
            timeout=5.0,
        )
        try:
            # Simple query to verify connection
            result = await conn.fetchval("SELECT 1")
            latency_ms = (time.perf_counter() - start) * 1000

            if result == 1:
                return DependencyHealth(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency_ms,
                    message="Connected and responsive",
                )
            else:
                return DependencyHealth(
                    name="database",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency_ms,
                    message="Unexpected query result",
                )
        finally:
            await conn.close()

    except asyncio.TimeoutError:
        return DependencyHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message="Connection timeout (>5s)",
        )
    except ImportError:
        # Fallback to synchronous check if asyncpg not available
        return await _check_database_sync()
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return DependencyHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Connection failed: {type(e).__name__}",
        )


def _check_database_sync_impl() -> DependencyHealth:
    """Synchronous database check implementation."""
    try:
        from sqlalchemy import create_engine, text

        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            return DependencyHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message="DATABASE_URL not configured",
            )

        start = time.perf_counter()
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = (time.perf_counter() - start) * 1000

        return DependencyHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            latency_ms=latency_ms,
            message="Connected (sync)",
        )
    except Exception as e:
        return DependencyHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Connection failed: {type(e).__name__}",
        )


async def _check_database_sync() -> DependencyHealth:
    """Synchronous database check fallback run in thread pool."""
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _check_database_sync_impl)


async def check_redis_health() -> DependencyHealth:
    """Check Redis connectivity and latency."""
    try:
        import redis.asyncio as aioredis

        redis_url = os.getenv("REDIS_URL", "")
        if not redis_url:
            return DependencyHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                message="REDIS_URL not configured (using fallbacks)",
            )

        start = time.perf_counter()
        client = aioredis.from_url(redis_url, decode_responses=True)
        try:
            # Execute ping command - type ignore due to redis-py stub issues
            pong = await client.ping()  # type: ignore[misc]
            latency_ms = (time.perf_counter() - start) * 1000

            # Get memory info for details
            info = await client.info("memory")  # type: ignore[misc]

            return DependencyHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                latency_ms=latency_ms,
                message="Connected and responsive" if pong else "Unexpected response",
                details={
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "maxmemory_human": info.get("maxmemory_human", "unlimited"),
                },
            )
        finally:
            await client.aclose()

    except asyncio.TimeoutError:
        return DependencyHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message="Connection timeout (>2s)",
        )
    except ImportError:
        return DependencyHealth(
            name="redis",
            status=HealthStatus.DEGRADED,
            message="redis package not installed",
        )
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return DependencyHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Connection failed: {type(e).__name__}",
        )


async def check_minio_health() -> DependencyHealth:
    """Check MinIO/S3 storage availability."""
    try:
        import httpx

        minio_endpoint = os.getenv("MINIO_ENDPOINT", os.getenv("S3_ENDPOINT", ""))
        if not minio_endpoint:
            return DependencyHealth(
                name="storage",
                status=HealthStatus.DEGRADED,
                message="MINIO_ENDPOINT/S3_ENDPOINT not configured",
            )

        # Ensure endpoint has protocol
        if not minio_endpoint.startswith(("http://", "https://")):
            minio_endpoint = f"http://{minio_endpoint}"

        # MinIO has a /minio/health/live endpoint
        health_url = f"{minio_endpoint}/minio/health/live"

        start = time.perf_counter()
        async with httpx.AsyncClient() as client:
            response = await asyncio.wait_for(
                client.get(health_url),
                timeout=3.0,
            )
            latency_ms = (time.perf_counter() - start) * 1000

            if response.status_code == 200:
                return DependencyHealth(
                    name="storage",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency_ms,
                    message="MinIO storage available",
                )
            else:
                return DependencyHealth(
                    name="storage",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency_ms,
                    message=f"MinIO returned status {response.status_code}",
                )

    except asyncio.TimeoutError:
        return DependencyHealth(
            name="storage",
            status=HealthStatus.UNHEALTHY,
            message="Connection timeout (>3s)",
        )
    except ImportError:
        return DependencyHealth(
            name="storage",
            status=HealthStatus.DEGRADED,
            message="httpx package not installed",
        )
    except Exception as e:
        logger.warning(f"MinIO health check failed: {e}")
        return DependencyHealth(
            name="storage",
            status=HealthStatus.DEGRADED,
            message=f"Check failed: {type(e).__name__}",
        )


async def run_all_health_checks() -> HealthCheckResult:
    """Run all health checks concurrently."""
    # Run checks in parallel
    results = await asyncio.gather(
        check_database_health(),
        check_redis_health(),
        check_minio_health(),
        return_exceptions=True,
    )

    dependencies: list[DependencyHealth] = []
    for result in results:
        if isinstance(result, BaseException):
            dependencies.append(
                DependencyHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {type(result).__name__}",
                )
            )
        elif isinstance(result, DependencyHealth):
            dependencies.append(result)

    # Determine overall status
    statuses = [dep.status for dep in dependencies]
    if HealthStatus.UNHEALTHY in statuses:
        overall_status = HealthStatus.UNHEALTHY
    elif HealthStatus.DEGRADED in statuses:
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.HEALTHY

    return HealthCheckResult(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=os.getenv("APP_VERSION", "unknown"),
        uptime_seconds=time.time() - _startup_time,
        dependencies=dependencies,
    )


def create_health_router() -> APIRouter:
    """Create router with health check endpoints."""
    router = APIRouter(tags=["Health"])

    @router.get("/health", include_in_schema=False)
    async def health_check() -> dict[str, Any]:
        """Full health check with dependency status.

        Returns detailed health information including:
        - Overall status (healthy/degraded/unhealthy)
        - Individual dependency status
        - Latency measurements
        - Service metadata

        Use for monitoring dashboards and alerting.
        """
        result = await run_all_health_checks()
        return result.to_dict()

    @router.get("/ready", include_in_schema=False)
    async def readiness_probe(response: Response) -> dict[str, str]:
        """Kubernetes readiness probe.

        Returns 200 if the service can accept traffic.
        Returns 503 if critical dependencies are unavailable.

        Used by load balancers to determine if traffic should be routed.
        """
        # Only check database for readiness (critical path)
        db_health = await check_database_health()

        if db_health.status == HealthStatus.UNHEALTHY:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "not_ready",
                "reason": db_health.message or "database unavailable",
            }

        return {"status": "ready"}

    @router.get("/live", include_in_schema=False)
    async def liveness_probe() -> dict[str, str]:
        """Kubernetes liveness probe.

        Returns 200 if the process is alive and responding.
        This is a lightweight check - no external dependencies.

        Used by Kubernetes to determine if the pod should be restarted.
        """
        return {"status": "alive"}

    return router


# Create router instance for import
health_router = create_health_router()


__all__ = [
    "DependencyHealth",
    "HealthCheckResult",
    "HealthStatus",
    "check_database_health",
    "check_minio_health",
    "check_redis_health",
    "create_health_router",
    "health_router",
    "run_all_health_checks",
]
