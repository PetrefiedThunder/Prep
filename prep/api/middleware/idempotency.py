"""Middleware enforcing idempotency semantics for mutating requests."""

from __future__ import annotations

import hashlib
from typing import Any, Awaitable, Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from prep.api.errors import json_error_response
from prep.cache import RedisProtocol, get_redis

_MUTATING_METHODS = {"POST", "PUT"}


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Ensure POST/PUT requests provide stable idempotency keys."""

    def __init__(self, app: ASGIApp, *, ttl_seconds: int = 6 * 60 * 60) -> None:
        super().__init__(app)
        self._ttl_seconds = ttl_seconds

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.method not in _MUTATING_METHODS:
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return json_error_response(
                request,
                status_code=status.HTTP_400_BAD_REQUEST,
                code="api.idempotency.missing_key",
                message="Idempotency-Key header is required for POST and PUT requests",
            )

        request.state.idempotency_key = idempotency_key

        body = await request.body()
        request._body = body  # type: ignore[attr-defined]

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive  # type: ignore[attr-defined]

        signature = self._build_signature(request, body)
        cache_key = self._cache_key(request, idempotency_key)

        redis: RedisProtocol = await get_redis()
        cached_signature = await redis.get(cache_key)
        if cached_signature is not None:
            if cached_signature != signature:
                return json_error_response(
                    request,
                    status_code=status.HTTP_409_CONFLICT,
                    code="api.idempotency.payload_conflict",
                    message="Idempotency key reuse detected with a different payload",
                )
            return json_error_response(
                request,
                status_code=status.HTTP_409_CONFLICT,
                code="api.idempotency.replayed",
                message="Request with this Idempotency-Key has already been processed",
            )

        await redis.setex(cache_key, self._ttl_seconds, signature)

        response = await call_next(request)
        response.headers.setdefault("Idempotency-Key", idempotency_key)

        if response.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            await redis.delete(cache_key)

        return response

    def _cache_key(self, request: Request, idempotency_key: str) -> str:
        route = request.url.path
        return f"idempotency:{route}:{idempotency_key}"

    @staticmethod
    def _build_signature(request: Request, body: bytes) -> str:
        hasher = hashlib.sha256()
        hasher.update(request.method.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(request.url.path.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(body)
        return hasher.hexdigest()


__all__ = ["IdempotencyMiddleware"]
