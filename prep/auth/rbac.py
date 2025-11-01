"""Role-based access control helpers for Prep services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Iterable, Mapping, Sequence

import jwt
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from prep.settings import Settings

# ---- Role declarations -----------------------------------------------------


RBAC_ROLES: set[str] = {
    "operator_admin",
    "kitchen_manager",
    "food_business_admin",
    "city_reviewer",
    "support_analyst",
    "regulatory_admin",
}


def _normalize_roles(roles: Iterable[str]) -> set[str]:
    """Return a normalized set of string roles."""

    normalized: set[str] = set()
    for role in roles:
        if not isinstance(role, str):
            continue
        value = role.strip()
        if value:
            normalized.add(value)
    return normalized


def require_roles(*roles: str) -> Callable[[Callable[..., object]], Callable[..., object]]:
    """Attach RBAC role requirements to an endpoint function."""

    required = frozenset(_normalize_roles(roles))

    def decorator(func: Callable[..., object]) -> Callable[..., object]:
        setattr(func, "__rbac_roles__", required)
        return func

    return decorator


@dataclass(frozen=True)
class RBACRule:
    """Route prefix to role mapping."""

    path_prefix: str
    roles: tuple[str, ...]


class RBACMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware enforcing JWT role claims before routing requests."""

    def __init__(
        self,
        app: ASGIApp,
        settings: Settings,
        *,
        route_roles: Mapping[str, Iterable[str]] | None = None,
        exempt_paths: Sequence[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._settings = settings
        self._exempt_paths: tuple[str, ...] = tuple(
            path.rstrip("/") for path in (exempt_paths or settings.rbac_excluded_paths)
        )

        if route_roles:
            rules = [
                RBACRule(path_prefix=prefix.rstrip("/"), roles=tuple(_normalize_roles(roles)))
                for prefix, roles in route_roles.items()
            ]
        else:
            rules = [
                RBACRule(
                    path_prefix=policy.path_prefix.rstrip("/"),
                    roles=tuple(_normalize_roles(policy.roles)),
                )
                for policy in settings.rbac_policies
            ]
        self._rules: tuple[RBACRule, ...] = tuple(rule for rule in rules if rule.roles)

    async def dispatch(  # type: ignore[override]
        self, request: StarletteRequest, call_next: Callable[[StarletteRequest], Awaitable[Response]]
    ) -> Response:
        path = request.url.path.rstrip("/")
        if any(path.startswith(prefix) for prefix in self._exempt_paths if prefix):
            return await call_next(request)

        required_roles = self._resolve_required_roles(request)
        if not required_roles:
            return await call_next(request)

        try:
            token = self._extract_token(request)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        try:
            roles = set(_decode_roles(token, self._settings))
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        except Exception as exc:  # pragma: no cover - defensive guard
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization token",
            ) from exc

        if not roles:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Missing RBAC role claims"},
            )

        if required_roles.isdisjoint(roles):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Insufficient RBAC permissions"},
            )

        return await call_next(request)

    def _resolve_required_roles(self, request: Request) -> set[str]:
        endpoint = request.scope.get("endpoint")
        if endpoint is not None:
            explicit_roles = getattr(endpoint, "__rbac_roles__", None)
            if explicit_roles:
                return _normalize_roles(explicit_roles)

        path = request.url.path.rstrip("/")
        for rule in self._rules:
            if not rule.path_prefix:
                continue
            if path == rule.path_prefix or path.startswith(f"{rule.path_prefix}/"):
                return _normalize_roles(rule.roles)
        return set()

    @staticmethod
    def _extract_token(request: Request) -> str:
        auth_header = request.headers.get("Authorization")
        if not auth_header or " " not in auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        scheme, token = auth_header.split(" ", 1)
        if scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer token required",
            )
        return token.strip()


__all__ = ["RBACMiddleware", "RBACRule", "require_roles", "RBAC_ROLES"]


_ALLOWED_JWT_ALGORITHMS: tuple[str, ...] = ("HS256", "RS256")


def _decode_roles(token: str, settings: Settings) -> list[str]:
    header = jwt.get_unverified_header(token)
    algorithm = header.get("alg")
    if algorithm not in _ALLOWED_JWT_ALGORITHMS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unsupported token algorithm")

    signing_key = settings.auth_signing_key or settings.secret_key
    payload = jwt.decode(
        token,
        signing_key,
        algorithms=_ALLOWED_JWT_ALGORITHMS,
        audience=settings.oidc_audience if settings.oidc_audience else None,
        options={"verify_aud": bool(settings.oidc_audience)},
    )

    raw_roles = payload.get("roles", [])
    if isinstance(raw_roles, str):
        raw_roles = [raw_roles]
    if not isinstance(raw_roles, Iterable):
        return []
    roles: list[str] = []
    for value in raw_roles:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                roles.append(normalized)
    return roles
