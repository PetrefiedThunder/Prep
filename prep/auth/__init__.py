"""Authentication helpers and shared dependencies for Prep services."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database import get_db
from prep.models.orm import User, UserRole
from prep.settings import Settings, get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


_ALLOWED_JWT_ALGORITHMS: tuple[str, ...] = ("HS256",)


def _extract_roles(payload: dict[str, Any]) -> list[str]:
    """Normalize the ``roles`` claim from a decoded JWT payload."""

    raw_roles = payload.get("roles", [])
    if isinstance(raw_roles, str):
        raw_roles = [raw_roles]
    if not isinstance(raw_roles, (list, tuple, set)):
        return []
    roles: list[str] = []
    for value in raw_roles:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                roles.append(normalized)
    return roles


def _decode_jwt(token: str, settings: Settings) -> dict[str, Any]:
    """Decode and validate a JWT payload."""

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
        ) from exc

    algorithm = header.get("alg")
    if algorithm not in _ALLOWED_JWT_ALGORITHMS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unsupported token algorithm",
        )

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=_ALLOWED_JWT_ALGORITHMS,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return payload


def get_token_roles(token: str, settings: Settings) -> list[str]:
    """Return the normalized role claims encoded in ``token``."""

    payload = _decode_jwt(token, settings)
    return _extract_roles(payload)


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Resolve and authorize the currently authenticated admin user."""

    user, roles = await _resolve_user(token, db, settings)
    if "admin" not in roles and not user.is_admin and user.role is not UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    if user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Resolve the currently authenticated user for analytics endpoints."""

    user, roles = await _resolve_user(token, db, settings)
    if user.is_suspended or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )

    if not roles and user.role not in {UserRole.ADMIN, UserRole.HOST, UserRole.CUSTOMER}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return user


async def _resolve_user(
    token: str, db: AsyncSession, settings: Settings
) -> tuple[User, list[str]]:
    """Decode the token and load the associated user."""

    payload = _decode_jwt(token, settings)
    subject = payload.get("sub")
    roles = _extract_roles(payload)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    try:
        user_id = UUID(str(subject))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid subject claim",
        ) from exc

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user, roles


__all__ = [
    "get_current_admin",
    "get_current_user",
    "get_token_roles",
    "oauth2_scheme",
    "_decode_jwt",
]

