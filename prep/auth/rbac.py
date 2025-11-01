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

"""Role-based access control middleware for the Prep API gateway."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from fastapi import status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from prep.auth import decode_token
from prep.settings import Settings


@dataclass(frozen=True)
class RBACRule:
    """Route prefix to role mapping used by :class:`RBACMiddleware`."""

    path_prefix: str
    roles: Sequence[str]


class RBACMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing that incoming requests include authorized roles."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings
        self._rules: list[RBACRule] = [
            RBACRule(path_prefix=rule.path_prefix, roles=tuple(rule.roles))
            for rule in settings.rbac_policies
        ]
        self._excluded: tuple[str, ...] = tuple(settings.rbac_excluded_paths)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self._excluded):
            return await call_next(request)

        rule = self._match_rule(path)
        if rule is None:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or " " not in auth_header:
            return self._error_response(status.HTTP_401_UNAUTHORIZED, "Authentication required")

        scheme, token = auth_header.split(" ", 1)
        if scheme.lower() != "bearer" or not token.strip():
            return self._error_response(status.HTTP_401_UNAUTHORIZED, "Bearer token required")

        try:
            payload = decode_token(token.strip(), self._settings)
        except Exception:  # pragma: no cover - handled by decode_token
            return self._error_response(status.HTTP_401_UNAUTHORIZED, "Invalid token")

        roles: Iterable[str]
        token_roles = payload.get("roles")
        if isinstance(token_roles, str):
            roles = [token_roles]
        elif isinstance(token_roles, Iterable):
            roles = [str(role) for role in token_roles]
        else:
            roles = []

        if not any(role in rule.roles for role in roles):
            return self._error_response(status.HTTP_403_FORBIDDEN, "Insufficient role")

        return await call_next(request)

    def _match_rule(self, path: str) -> RBACRule | None:
        for rule in self._rules:
            if path.startswith(rule.path_prefix):
                return rule
        return None

    @staticmethod
    def _error_response(status_code: int, message: str) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": message})


__all__ = ["RBACMiddleware", "RBACRule"]
