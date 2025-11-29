"""Database connection pool configuration and monitoring.

This module provides:
- Production-ready connection pool settings
- Pool health monitoring
- Connection pool metrics for Prometheus
- Configuration recommendations

Connection Pool Best Practices:
------------------------------
1. pool_size: Number of persistent connections
   - Set based on expected concurrent database operations
   - Rule of thumb: number of worker processes * connections per worker
   - Too low: connection contention and timeouts
   - Too high: database resource exhaustion

2. max_overflow: Additional connections beyond pool_size
   - Handles traffic spikes without exhausting database
   - Set to 0 for strict pool limits
   - Set higher for bursty workloads

3. pool_timeout: Seconds to wait for available connection
   - Prevents indefinite blocking
   - Should be less than request timeout
   - 30 seconds is reasonable default

4. pool_recycle: Connection lifetime in seconds
   - Prevents stale connections after database restarts
   - Set lower than database's wait_timeout
   - 1800 (30 min) is conservative default

5. pool_pre_ping: Test connection before use
   - Detects stale connections before errors occur
   - Small overhead but prevents connection errors
   - Always enable in production
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from prep.observability.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PoolConfig:
    """Database connection pool configuration."""

    # Core pool settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800
    pool_pre_ping: bool = True

    # Advanced settings
    echo: bool = False
    echo_pool: bool = False
    future: bool = True

    @classmethod
    def from_environment(cls) -> PoolConfig:
        """Load configuration from environment variables."""
        return cls(
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
            pool_pre_ping=os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            echo_pool=os.getenv("DB_ECHO_POOL", "false").lower() == "true",
        )

    @classmethod
    def for_environment(cls, environment: str) -> PoolConfig:
        """Get recommended configuration for an environment.

        Args:
            environment: One of 'development', 'staging', 'production'

        Returns:
            Appropriate PoolConfig for the environment
        """
        configs = {
            "development": cls(
                pool_size=5,
                max_overflow=5,
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True,
                echo=True,
            ),
            "staging": cls(
                pool_size=10,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=True,
                echo=False,
            ),
            "production": cls(
                pool_size=20,
                max_overflow=30,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=True,
                echo=False,
            ),
        }
        return configs.get(environment.lower(), configs["development"])

    def to_engine_kwargs(self) -> dict[str, Any]:
        """Convert to SQLAlchemy engine keyword arguments."""
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
            "echo": self.echo,
            "echo_pool": self.echo_pool,
            "future": self.future,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/monitoring."""
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
            "echo": self.echo,
        }


@dataclass
class PoolStats:
    """Statistics about connection pool usage."""

    pool_size: int
    checked_in: int
    checked_out: int
    overflow: int
    invalid: int
    total_connections: int
    available_connections: int
    utilization_percent: float

    @classmethod
    def from_pool(cls, pool: Any) -> PoolStats:
        """Extract statistics from a SQLAlchemy pool.

        Args:
            pool: SQLAlchemy connection pool

        Returns:
            PoolStats instance
        """
        status = pool.status()
        pool_size = pool.size()
        checked_out = pool.checkedout()
        overflow = pool.overflow()
        checked_in = pool.checkedin()

        total = pool_size + overflow
        available = checked_in
        utilization = (checked_out / total * 100) if total > 0 else 0

        return cls(
            pool_size=pool_size,
            checked_in=checked_in,
            checked_out=checked_out,
            overflow=overflow,
            invalid=getattr(pool, "_invalidated", 0),
            total_connections=total,
            available_connections=available,
            utilization_percent=round(utilization, 2),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pool_size": self.pool_size,
            "checked_in": self.checked_in,
            "checked_out": self.checked_out,
            "overflow": self.overflow,
            "invalid": self.invalid,
            "total_connections": self.total_connections,
            "available_connections": self.available_connections,
            "utilization_percent": self.utilization_percent,
        }

    def is_healthy(self, warning_threshold: float = 80.0) -> bool:
        """Check if pool utilization is healthy."""
        return self.utilization_percent < warning_threshold


class PoolMonitor:
    """Monitor database connection pool health.

    Usage:
        monitor = PoolMonitor(engine.pool)
        stats = monitor.get_stats()

        # Check health
        if not stats.is_healthy():
            logger.warning("Connection pool under pressure")
    """

    def __init__(self, pool: Any):
        """Initialize monitor with a SQLAlchemy pool.

        Args:
            pool: SQLAlchemy connection pool (from engine.pool)
        """
        self.pool = pool
        self._last_check_time: float = 0
        self._last_stats: PoolStats | None = None

    def get_stats(self) -> PoolStats:
        """Get current pool statistics."""
        stats = PoolStats.from_pool(self.pool)
        self._last_check_time = time.time()
        self._last_stats = stats
        return stats

    def log_stats(self, level: str = "info") -> None:
        """Log current pool statistics.

        Args:
            level: Log level ('debug', 'info', 'warning')
        """
        stats = self.get_stats()
        log_func = getattr(logger, level)
        log_func(
            f"Connection pool status: {stats.utilization_percent}% utilized",
            extra=stats.to_dict(),
        )

    def check_health(
        self,
        warning_threshold: float = 80.0,
        critical_threshold: float = 95.0,
    ) -> tuple[str, PoolStats]:
        """Check pool health and return status.

        Args:
            warning_threshold: Utilization % to trigger warning
            critical_threshold: Utilization % to trigger critical

        Returns:
            Tuple of (status, stats) where status is 'healthy', 'warning', or 'critical'
        """
        stats = self.get_stats()

        if stats.utilization_percent >= critical_threshold:
            status = "critical"
            logger.error(
                f"Connection pool critical: {stats.utilization_percent}% utilized",
                extra=stats.to_dict(),
            )
        elif stats.utilization_percent >= warning_threshold:
            status = "warning"
            logger.warning(
                f"Connection pool warning: {stats.utilization_percent}% utilized",
                extra=stats.to_dict(),
            )
        else:
            status = "healthy"

        return status, stats


def get_pool_metrics_for_prometheus(pool: Any) -> dict[str, float]:
    """Get pool metrics in Prometheus-compatible format.

    Args:
        pool: SQLAlchemy connection pool

    Returns:
        Dictionary of metric names to values
    """
    stats = PoolStats.from_pool(pool)

    return {
        "db_pool_size": float(stats.pool_size),
        "db_pool_checked_in": float(stats.checked_in),
        "db_pool_checked_out": float(stats.checked_out),
        "db_pool_overflow": float(stats.overflow),
        "db_pool_total_connections": float(stats.total_connections),
        "db_pool_available_connections": float(stats.available_connections),
        "db_pool_utilization_percent": stats.utilization_percent,
    }


# Configuration recommendations based on workload
POOL_SIZING_GUIDE = """
Database Connection Pool Sizing Guide
=====================================

Small Application (< 100 req/sec):
  pool_size: 5
  max_overflow: 5
  Total max connections: 10

Medium Application (100-1000 req/sec):
  pool_size: 10-20
  max_overflow: 10-20
  Total max connections: 20-40

Large Application (> 1000 req/sec):
  pool_size: 20-50
  max_overflow: 30-50
  Total max connections: 50-100

Kubernetes Considerations:
- Multiply by number of pods
- Example: 10 pods × 10 pool_size = 100 database connections
- Ensure database max_connections > total pool connections

PostgreSQL max_connections:
- Default: 100
- Recommended for production: 200-500
- Formula: (pods × pool_size × 1.5) for headroom

Common Issues:
1. "too many connections" → Reduce pool_size or add more database replicas
2. "connection timeout" → Increase pool_timeout or pool_size
3. Stale connections → Reduce pool_recycle
"""


__all__ = [
    "POOL_SIZING_GUIDE",
    "PoolConfig",
    "PoolMonitor",
    "PoolStats",
    "get_pool_metrics_for_prometheus",
]
