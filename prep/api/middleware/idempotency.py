"""Middleware enforcing API idempotency semantics for mutating requests."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from prep.cache import get_redis
from prep.platform.schemas import ErrorDetail, ErrorResponseEnvelope, resolve_request_id

_CACHE_PREFIX = "idempotency"
_DEFAULT_TTL_SECONDS = 24 * 60 * 60


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Validate `Idempotency-Key` headers and replay cached responses."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        super().__init__(app)
        self._ttl_seconds = ttl_seconds

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method not in {"POST", "PUT"}:
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
            return self._error_response(
                request,
                status.HTTP_400_BAD_REQUEST,
                "idempotency.missing_key",
                "Idempotency-Key header is required for mutating requests",
                idempotency_key,
            )

        body = await request.body()
        request._body = body  # cache the body for downstream handlers
        signature = self._compute_signature(request, body, idempotency_key)
        redis = await get_redis()
        cache_key = f"{_CACHE_PREFIX}:{idempotency_key}"

        cached_raw = await redis.get(cache_key)
        cached: dict[str, Any] | None = None
        if cached_raw:
            try:
                cached = json.loads(cached_raw)
            except (TypeError, json.JSONDecodeError):
                cached = None

        if cached:
            stored_hash = cached.get("hash")
            if stored_hash and stored_hash != signature:
                return self._error_response(
                    request,
                    status.HTTP_409_CONFLICT,
                    "idempotency.key_conflict",
                    "Idempotency-Key re-use detected with a different payload",
                    idempotency_key,
                )
            if cached.get("status_code") is None:
                return self._error_response(
                    request,
                    status.HTTP_409_CONFLICT,
                    "idempotency.in_progress",
                    "A request with this Idempotency-Key is currently being processed",
                    idempotency_key,
                )
            return self._build_cached_response(request, idempotency_key, cached)

        placeholder = json.dumps({"hash": signature, "status_code": None})
        await redis.setex(cache_key, self._ttl_seconds, placeholder)

        response = await call_next(request)
        response = await self._capture_response(
            request, response, redis, cache_key, signature, idempotency_key
        )
        return response

    @staticmethod
    def _compute_signature(request: Request, body: bytes, key: str) -> str:
        digest = hashlib.sha256()
        digest.update(key.encode("utf-8"))
        digest.update(request.method.encode("utf-8"))
        digest.update(request.url.path.encode("utf-8"))
        digest.update(body)
        return digest.hexdigest()

    def _error_response(
        self,
        request: Request,
        status_code: int,
        code: str,
        message: str,
        key: str | None,
    ) -> JSONResponse:
        request_id = resolve_request_id(request)
        envelope = ErrorResponseEnvelope(
            request_id=request_id,
            error=ErrorDetail(code=code, message=message),
        )
        response = JSONResponse(status_code=status_code, content=envelope.model_dump())
        response.headers["X-Request-ID"] = request_id
        if key:
            response.headers["Idempotency-Key"] = key
        return response

    async def _capture_response(
        self,
        request: Request,
        response: Response,
        redis,
        cache_key: str,
        signature: str,
        key: str,
    ) -> Response:
        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk
        encoded_body = base64.b64encode(body_bytes).decode("utf-8")
        headers = {k: v for k, v in response.headers.items()}
        headers["Idempotency-Key"] = key
        headers.setdefault("X-Request-ID", resolve_request_id(request))

        cached_payload = {
            "hash": signature,
            "status_code": response.status_code,
            "media_type": response.media_type,
            "headers": headers,
            "body": encoded_body,
        }
        await redis.setex(cache_key, self._ttl_seconds, json.dumps(cached_payload))

        new_response = Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
        return new_response

    def _build_cached_response(
        self,
        request: Request,
        key: str,
        cached: dict[str, Any],
    ) -> Response:
        body_b64 = cached.get("body")
        try:
            body = base64.b64decode(body_b64) if body_b64 else b""
        except (TypeError, ValueError):
            body = b""
        headers = {k: v for k, v in cached.get("headers", {}).items()}
        headers["Idempotency-Key"] = key
        headers.setdefault("X-Request-ID", resolve_request_id(request))
        headers["Idempotent-Replay"] = "true"
        return Response(
            content=body,
            status_code=cached.get("status_code", status.HTTP_200_OK),
            headers=headers,
            media_type=cached.get("media_type"),
        )
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
