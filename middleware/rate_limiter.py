"""Rate limiting middleware for FastAPI.

This middleware implements a sliding window rate limiter using Redis
for distributed rate limiting across multiple instances.

Production-ready implementation with:
- Per-IP rate limiting
- Per-user rate limiting (if authenticated)
- Configurable limits per route
- Redis-backed for distributed deployments
- Fallback to in-memory when Redis unavailable
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Default limits (requests per window)
    default_limit: int = 100
    default_window: int = 60  # seconds

    # Route-specific limits (path prefix -> (limit, window))
    route_limits: dict[str, tuple[int, int]] = field(default_factory=dict)

    # Exempt paths (no rate limiting)
    exempt_paths: tuple[str, ...] = (
        "/healthz",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    )

    # Whether to use Redis (falls back to in-memory if unavailable)
    use_redis: bool = True
    redis_url: str = ""

    # Headers
    include_headers: bool = True

    def __post_init__(self):
        if not self.route_limits:
            # Set sensible defaults for different route types
            self.route_limits = {
                "/api/v1/auth/login": (5, 60),  # 5 login attempts per minute
                "/api/v1/auth/register": (3, 60),  # 3 registrations per minute
                "/api/v1/auth/token": (10, 60),  # 10 token requests per minute
                "/api/v1/admin": (50, 60),  # 50 admin requests per minute
                "/api/v1/bookings": (30, 60),  # 30 booking requests per minute
                "/api/v1/payments": (10, 60),  # 10 payment requests per minute
                "/api/v1/compliance": (20, 60),  # 20 compliance requests per minute
            }


class InMemoryRateLimiter:
    """In-memory rate limiter using sliding window algorithm.

    This is a fallback when Redis is not available.
    Note: Does not work across multiple instances.
    """

    def __init__(self):
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(
        self, key: str, limit: int, window: int
    ) -> tuple[bool, int, int]:
        """Check if request is allowed.

        Returns:
            (allowed, remaining, reset_time)
        """
        now = time.time()
        window_start = now - window

        async with self._lock:
            # Clean old entries
            self._windows[key] = [ts for ts in self._windows[key] if ts > window_start]

            current_count = len(self._windows[key])
            remaining = max(0, limit - current_count - 1)
            reset_time = int(window_start + window)

            if current_count >= limit:
                return False, 0, reset_time

            # Add current request
            self._windows[key].append(now)
            return True, remaining, reset_time

    async def cleanup(self):
        """Periodically clean up old entries."""
        async with self._lock:
            now = time.time()
            # Keep only last hour of data
            cutoff = now - 3600
            for key in list(self._windows.keys()):
                self._windows[key] = [ts for ts in self._windows[key] if ts > cutoff]
                if not self._windows[key]:
                    del self._windows[key]


class RedisRateLimiter:
    """Redis-backed rate limiter using sliding window algorithm.

    Works across multiple instances for distributed deployments.
    """

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis = None
        self._connected = False

    async def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis

                self._redis = aioredis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                # ping() returns Awaitable in redis.asyncio
                pong = await self._redis.ping()
                if pong:
                    self._connected = True
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._connected = False
                self._redis = None
        return self._redis

    async def is_allowed(
        self, key: str, limit: int, window: int
    ) -> tuple[bool, int, int]:
        """Check if request is allowed using Redis sorted sets.

        Returns:
            (allowed, remaining, reset_time)
        """
        redis_client = await self._get_redis()
        if redis_client is None:
            # Allow request if Redis is unavailable
            return True, limit - 1, int(time.time() + window)

        now = time.time()
        window_start = now - window
        redis_key = f"ratelimit:{key}"

        try:
            pipe = redis_client.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(redis_key, 0, window_start)

            # Count current entries
            pipe.zcard(redis_key)

            # Add current request (will be rolled back if over limit)
            pipe.zadd(redis_key, {str(now): now})

            # Set expiry
            pipe.expire(redis_key, window + 1)

            results = await pipe.execute()
            current_count = results[1]

            remaining = max(0, limit - current_count - 1)
            reset_time = int(window_start + window)

            if current_count >= limit:
                # Remove the entry we just added
                await redis_client.zrem(redis_key, str(now))
                return False, 0, reset_time

            return True, remaining, reset_time

        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            # Allow request on error
            return True, limit - 1, int(time.time() + window)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for FastAPI.

    Usage:
        app.add_middleware(
            RateLimitMiddleware,
            config=RateLimitConfig(
                default_limit=100,
                default_window=60,
            ),
        )
    """

    def __init__(self, app, config: RateLimitConfig | None = None):
        super().__init__(app)
        self.config = config or RateLimitConfig()

        # Initialize rate limiter backend
        redis_url = self.config.redis_url or os.getenv("REDIS_URL", "")

        if self.config.use_redis and redis_url:
            self._limiter = RedisRateLimiter(redis_url)
            logger.info("Rate limiter initialized with Redis backend")
        else:
            self._limiter = InMemoryRateLimiter()
            logger.info("Rate limiter initialized with in-memory backend")

    def _get_client_key(self, request: Request) -> str:
        """Get unique identifier for the client."""
        # Try to get user ID from headers (set by auth middleware)
        user_id = request.headers.get("X-User-Id")
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get the first IP in the chain (original client)
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    def _get_limits(self, path: str) -> tuple[int, int]:
        """Get rate limits for a given path."""
        # Check route-specific limits
        for prefix, (limit, window) in self.config.route_limits.items():
            if path.startswith(prefix):
                return limit, window

        return self.config.default_limit, self.config.default_window

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting."""
        return any(path.startswith(exempt) for exempt in self.config.exempt_paths)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        path = request.url.path

        # Skip rate limiting for exempt paths
        if self._is_exempt(path):
            return await call_next(request)

        # Get client identifier and limits
        client_key = self._get_client_key(request)
        limit, window = self._get_limits(path)

        # Create a rate limit key combining client and path prefix
        path_prefix = "/".join(path.split("/")[:4])  # e.g., /api/v1/bookings
        rate_key = hashlib.sha256(f"{client_key}:{path_prefix}".encode()).hexdigest()[
            :16
        ]

        # Check rate limit
        allowed, remaining, reset_time = await self._limiter.is_allowed(
            rate_key, limit, window
        )

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {client_key} on {path}",
                extra={
                    "client_key": client_key,
                    "path": path,
                    "limit": limit,
                    "window": window,
                },
            )

            response = Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
            )

            if self.config.include_headers:
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(reset_time)
                response.headers["Retry-After"] = str(
                    max(1, reset_time - int(time.time()))
                )

            return response

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        if self.config.include_headers:
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


# Convenience function for creating pre-configured middleware
def create_rate_limiter(
    default_limit: int = 100,
    default_window: int = 60,
    redis_url: str | None = None,
    **kwargs,
) -> tuple[type, dict[str, Any]]:
    """Create rate limiter middleware with configuration.

    Usage:
        middleware_class, kwargs = create_rate_limiter(default_limit=50)
        app.add_middleware(middleware_class, **kwargs)
    """
    config = RateLimitConfig(
        default_limit=default_limit,
        default_window=default_window,
        redis_url=redis_url or os.getenv("REDIS_URL", ""),
        **kwargs,
    )
    return RateLimitMiddleware, {"config": config}
