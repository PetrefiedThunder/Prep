"""Core authentication utilities for JWT validation and user authorization.

This module provides low-level, reusable authentication primitives that enforce
secure patterns including:
- JWT signature and expiry validation
- Database lookups to prevent deleted/suspended users from authenticating
- Role-based access control (RBAC)
- Active/suspended status checks

These helpers are designed to be composed into FastAPI dependencies.
"""

from __future__ import annotations

from uuid import UUID

import jwt
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.models.db import User, UserRole


def decode_and_validate_jwt(
    token: str,
    secret: str,
    audience: str | None = None,
    algorithms: list[str] | None = None,
) -> dict:
    """Decode and validate a JWT token.

    Args:
        token: The JWT token to decode
        secret: The secret key used to sign the token
        audience: Optional audience claim to validate
        algorithms: List of allowed algorithms (default: ["HS256"])

    Returns:
        The decoded JWT payload as a dictionary

    Raises:
        HTTPException(401): If token is invalid, expired, or has wrong audience
    """
    if algorithms is None:
        algorithms = ["HS256"]

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=algorithms,
            audience=audience,
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
    except jwt.InvalidSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload format",
        )

    return payload


async def load_user_from_db(
    user_id: UUID,
    session: AsyncSession,
    require_active: bool = True,
    require_role: UserRole | None = None,
) -> User:
    """Load a user from the database with authorization checks.

    This function ensures that authentication is always backed by database state,
    preventing deleted or suspended users from accessing the system even with
    valid JWTs.

    Args:
        user_id: The UUID of the user to load
        session: Active SQLAlchemy async session
        require_active: If True, ensure user.is_active=True and user.is_suspended=False
        require_role: If provided, ensure user has this specific role

    Returns:
        The User ORM instance from the database

    Raises:
        HTTPException(403): If user not found, inactive, suspended, or role mismatch
    """
    # Build query with role filter if specified
    query = select(User).where(User.id == user_id)

    if require_role is not None:
        query = query.where(User.role == require_role)

    if require_active:
        query = query.where(User.is_active.is_(True), User.is_suspended.is_(False))

    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        # Generic error message to avoid user enumeration
        if require_role is not None:
            detail = f"{require_role.value.title()} not authorized"
        else:
            detail = "User not authorized"

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )

    return user


__all__ = [
    "decode_and_validate_jwt",
    "load_user_from_db",
]
