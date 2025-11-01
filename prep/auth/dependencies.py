"""FastAPI dependencies for authn/z shared across routers."""

from __future__ import annotations

import json

from fastapi import Depends, HTTPException, Request, status

from prep.cache import RedisProtocol, get_redis
from prep.settings import Settings, get_settings


async def enforce_allowlists(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """Validate the request client IP and device identifiers against allowlists."""

    client = request.client
    client_ip = client.host if client else None
    if settings.ip_allowlist and client_ip not in settings.ip_allowlist:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="IP address not allowed",
        )

    device_id = request.headers.get("X-Device-Id")
    if settings.device_allowlist and device_id not in settings.device_allowlist:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device not allowlisted",
        )


async def require_active_session(
    request: Request,
    cache: RedisProtocol = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> None:
    """Ensure any authenticated request has an active session in Redis."""

    path = request.url.path
    if any(path.startswith(prefix) for prefix in settings.session_optional_paths):
        return

    auth_header = request.headers.get("Authorization")
    if not auth_header or " " not in auth_header:
        return

    scheme, token = auth_header.split(" ", 1)
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )

    session_key = f"session:{token.strip()}"
    payload = await cache.get(session_key)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )

    if isinstance(payload, str):
        try:
            request.state.session = json.loads(payload)
        except json.JSONDecodeError:  # pragma: no cover - defensive guard
            request.state.session = payload
    else:  # pragma: no cover - redis driver returns str in production
        request.state.session = payload


__all__ = ["enforce_allowlists", "require_active_session"]
