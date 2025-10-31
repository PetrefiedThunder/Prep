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
