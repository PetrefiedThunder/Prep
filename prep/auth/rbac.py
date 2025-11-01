"""Role-based access control middleware for the Prep API."""

from __future__ import annotations

from collections.abc import Awaitable, Mapping, Sequence
from typing import Callable, Iterable, MutableMapping

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from prep.auth import get_token_roles
from prep.settings import Settings


RBAC_ROLES: set[str] = {
    "operator_admin",
    "kitchen_manager",
    "food_business_admin",
    "city_reviewer",
    "support_analyst",
}


def _normalize_roles(roles: Iterable[str]) -> set[str]:
    normalized: set[str] = set()
    for role in roles:
        if not isinstance(role, str):
            continue
        value = role.strip()
        if value:
            normalized.add(value)
    return normalized


def require_roles(*roles: str) -> Callable[[Callable[..., object]], Callable[..., object]]:
    """Annotate an endpoint with RBAC role requirements."""

    required = _normalize_roles(roles)

    def decorator(func: Callable[..., object]) -> Callable[..., object]:
        setattr(func, "__rbac_roles__", required)
        return func

    return decorator


class RBACMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware enforcing JWT role claims before routing requests."""

    def __init__(
        self,
        app: Callable[..., object],
        settings: Settings,
        *,
        route_roles: Mapping[str, Iterable[str]] | None = None,
        exempt_paths: Sequence[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._settings = settings
        self._route_roles: MutableMapping[str, set[str]] = {
            prefix.rstrip("/"): _normalize_roles(roles)
            for prefix, roles in (route_roles or {}).items()
        }
        self._exempt_paths: tuple[str, ...] = tuple(exempt_paths or ())

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self._exempt_paths):
            return await call_next(request)

        required_roles = self._resolve_required_roles(request)
        if not required_roles:
            return await call_next(request)

        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        token = authorization.split(" ", 1)[1].strip()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        try:
            roles = set(get_token_roles(token, self._settings))
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization token",
            ) from exc

        if not roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing RBAC role claims",
            )

        if required_roles.isdisjoint(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient RBAC permissions",
            )

        return await call_next(request)

    def _resolve_required_roles(self, request: Request) -> set[str]:
        endpoint = request.scope.get("endpoint")
        if endpoint is not None:
            explicit_roles = getattr(endpoint, "__rbac_roles__", None)
            if explicit_roles:
                return _normalize_roles(explicit_roles)

        path = request.url.path.rstrip("/")
        for prefix, roles in self._route_roles.items():
            if not prefix:
                continue
            if path == prefix or path.startswith(prefix + "/"):
                return roles
        return set()


__all__ = ["RBACMiddleware", "require_roles", "RBAC_ROLES"]

