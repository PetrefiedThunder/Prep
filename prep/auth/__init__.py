"""Lightweight authentication helpers for tests and services."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from prep.settings import Settings, get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

_ALLOWED_JWT_ALGORITHMS: tuple[str, ...] = ("HS256", "RS256")


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OPERATOR_ADMIN = "operator_admin"
    SUPPORT_ANALYST = "support_analyst"
    REGULATORY_ADMIN = "regulatory_admin"
    HOST = "host"
    CUSTOMER = "customer"


@dataclass
class User:
    id: str
    role: UserRole
    is_admin: bool = False
    is_active: bool = True
    is_suspended: bool = False


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token header") from exc

    algorithm = header.get("alg")
    if algorithm not in _ALLOWED_JWT_ALGORITHMS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unsupported token algorithm")

    signing_key = settings.auth_signing_key or settings.secret_key
    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=_ALLOWED_JWT_ALGORITHMS,
            audience=settings.oidc_audience if settings.oidc_audience else None,
            options={"verify_aud": bool(settings.oidc_audience)},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token signature") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token payload")
    return payload


def _extract_roles(payload: Mapping[str, Any]) -> list[str]:
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


def get_token_roles(token: str, settings: Settings) -> list[str]:
    return _extract_roles(decode_token(token, settings))


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
) -> User:
    payload = decode_token(token, settings)
    roles = set(_extract_roles(payload))
    allowed = {
        UserRole.ADMIN.value,
        UserRole.OPERATOR_ADMIN.value,
        UserRole.SUPPORT_ANALYST.value,
        UserRole.REGULATORY_ADMIN.value,
    }
    if not roles.intersection(allowed):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
    subject = str(payload.get("sub", "anonymous"))
    primary_role = next(iter(roles)) if roles else UserRole.ADMIN.value
    return User(id=subject, role=UserRole(primary_role), is_admin=True)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
) -> User:
    payload = decode_token(token, settings)
    subject = str(payload.get("sub", "anonymous"))
    roles = _extract_roles(payload)
    role_value = roles[0] if roles else UserRole.CUSTOMER.value
    return User(id=subject, role=UserRole(role_value))


__all__ = [
    "User",
    "UserRole",
    "decode_token",
    "get_current_admin",
    "get_current_user",
    "get_token_roles",
    "oauth2_scheme",
]
