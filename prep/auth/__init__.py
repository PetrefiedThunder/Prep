"""Authentication helpers and dependencies used across the Prep API surface."""

from __future__ import annotations

from typing import Any, Iterable
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database import get_db
from prep.models.orm import User, UserRole
from prep.settings import Settings, get_settings

# The OAuth2 password flow used by the legacy admin and analytics surfaces.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


_ALLOWED_JWT_ALGORITHMS: tuple[str, ...] = ("HS256", "RS256")


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    """Decode and validate a JWT payload using the configured signing keys."""

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


def _decode_jwt(token: str, settings: Settings) -> dict[str, Any]:
    """Backwards compatible alias retained for the existing unit tests."""

    return decode_token(token, settings)


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Resolve and authorize the currently authenticated admin user."""

    user, roles = await _resolve_user(token, db, settings)
    if not _has_required_role(
        roles,
        {
            UserRole.ADMIN.value,
            UserRole.OPERATOR_ADMIN.value,
            UserRole.SUPPORT_ANALYST.value,
        },
    ) and not user.is_admin:
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

    allowed_roles = {
        UserRole.ADMIN.value,
        UserRole.HOST.value,
        UserRole.CUSTOMER.value,
        UserRole.OPERATOR_ADMIN.value,
        UserRole.KITCHEN_MANAGER.value,
        UserRole.FOOD_BUSINESS_ADMIN.value,
        UserRole.CITY_REVIEWER.value,
        UserRole.SUPPORT_ANALYST.value,
    }

    if not roles and user.role.value not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    if roles and not _has_required_role(roles, allowed_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return user


async def _resolve_user(
    token: str,
    db: AsyncSession,
    settings: Settings,
) -> tuple[User, list[str]]:
    """Decode the token and load the associated user."""

    payload = decode_token(token, settings)
    subject = payload.get("sub")
    roles = payload.get("roles", [])
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

    return user, roles if isinstance(roles, list) else [str(roles)]


def _has_required_role(roles: Iterable[str], required: Iterable[str]) -> bool:
    """Return ``True`` if the token roles intersect with ``required``."""

    role_set = {role for role in roles}
    required_set = {role for role in required}
    return bool(role_set.intersection(required_set))


__all__ = [
    "decode_token",
    "get_current_admin",
    "get_current_user",
    "oauth2_scheme",
    "_decode_jwt",
]
