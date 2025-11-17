"""Core authentication helpers shared across all auth dependencies.

This module provides low-level, reusable authentication primitives:
- JWT token decoding and validation
- Database user lookup with active status enforcement
- Admin role verification

These helpers are used by higher-level dependencies like get_current_user
and get_current_admin to eliminate code duplication.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import jwt
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.models.orm import User, UserRole


def decode_and_validate_jwt(
    token: str,
    secret: str,
    audience: str | None,
    algorithms: list[str],
) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string
        secret: Secret key for verification
        audience: Expected audience (optional)
        algorithms: Allowed algorithms (e.g., ["HS256", "RS256"])

    Returns:
        Decoded JWT payload as dictionary

    Raises:
        HTTPException: 401 if token is invalid, expired, or signature verification fails
    """
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret not configured",
        )

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
        ) from exc

    algorithm = header.get("alg")
    if algorithm not in algorithms:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unsupported token algorithm: {algorithm}",
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=algorithms,
            audience=audience if audience else None,
            options={"verify_aud": bool(audience)},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from exc
    except jwt.InvalidAudienceError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience",
        ) from exc
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


async def load_user_from_db(
    user_id: UUID,
    session: AsyncSession,
    require_active: bool = True,
    require_role: UserRole | None = None,
) -> User:
    """
    Load user from database with optional validation.

    Args:
        user_id: User's UUID
        session: Database session
        require_active: If True, raise 403 if user is not active or is suspended
        require_role: If specified, raise 403 if user doesn't have this role

    Returns:
        User ORM object

    Raises:
        HTTPException: 403 if user not found, inactive, suspended, or has wrong role
    """
    query = select(User).where(User.id == user_id)

    if require_active:
        query = query.where(User.is_active.is_(True), User.is_suspended.is_(False))

    if require_role:
        query = query.where(User.role == require_role)

    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        if require_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User not authorized (missing role: {require_role.value})",
            )
        if require_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not authorized (inactive or suspended)",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found",
        )

    return user


def verify_admin_roles(roles: set[str]) -> None:
    """
    Verify that at least one admin role is present.

    Args:
        roles: Set of role strings from JWT payload

    Raises:
        HTTPException: 403 if no admin roles found
    """
    allowed_admin_roles = {
        UserRole.ADMIN.value,
        UserRole.OPERATOR_ADMIN.value,
        UserRole.SUPPORT_ANALYST.value,
        UserRole.REGULATORY_ADMIN.value,
    }

    if not roles.intersection(allowed_admin_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )


__all__ = [
    "decode_and_validate_jwt",
    "load_user_from_db",
    "verify_admin_roles",
]
