"""Authentication and shared dependencies for the admin API."""

from __future__ import annotations

import os
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from prep.auth.core import decode_and_validate_jwt, load_user_from_db
from prep.database import get_db
from prep.models.admin import AdminUser
from prep.models.db import UserRole

_security = HTTPBearer(auto_error=False)


def _get_jwt_settings() -> tuple[str, str, str]:
    """Return the shared JWT configuration.

    Returns:
        Tuple of (secret, audience, algorithm) for admin JWT validation

    Raises:
        RuntimeError: If ADMIN_JWT_SECRET is not configured
    """
    secret = os.getenv("ADMIN_JWT_SECRET")
    if not secret:
        raise RuntimeError("ADMIN_JWT_SECRET environment variable must be configured")
    audience = os.getenv("ADMIN_JWT_AUDIENCE", "prep-admin")
    algorithm = os.getenv("ADMIN_JWT_ALGORITHM", "HS256")
    return secret, audience, algorithm


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """Validate the admin JWT and return the authenticated administrator.

    This dependency performs secure authentication by:
    1. Validating JWT signature, expiry, and audience
    2. Loading user from database (prevents deleted/suspended users)
    3. Enforcing role=ADMIN and is_active=True
    4. Checking is_suspended=False (real-time suspension enforcement)

    Args:
        credentials: Bearer token from Authorization header
        db: Active database session

    Returns:
        AdminUser with validated identity and permissions

    Raises:
        HTTPException(401): If credentials missing or JWT invalid
        HTTPException(403): If user not found, not admin, or not active
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    secret, audience, algorithm = _get_jwt_settings()

    # Step 1: Decode and validate JWT (signature, expiry, audience)
    payload = decode_and_validate_jwt(
        credentials.credentials,
        secret,
        audience=audience,
        algorithms=[algorithm],
    )

    # Step 2: Extract and validate subject claim
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        admin_id = UUID(str(subject))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        ) from exc

    # Step 3: Load user from database with role and active checks
    # This prevents deleted/suspended users from authenticating even with valid JWTs
    admin = await load_user_from_db(
        admin_id,
        db,
        require_active=True,
        require_role=UserRole.ADMIN,
    )

    # Step 4: Extract permissions from JWT payload
    permissions = payload.get("permissions", [])
    if not isinstance(permissions, list):
        permissions = []

    return AdminUser(
        id=admin.id,
        email=admin.email,
        full_name=admin.full_name,
        permissions=permissions,
    )
