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
    """Return the shared JWT configuration."""

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
    """Validate the admin JWT and return the authenticated administrator."""

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    secret, audience, algorithm = _get_jwt_settings()

    # Use shared JWT validation helper
    payload = decode_and_validate_jwt(
        token=credentials.credentials,
        secret=secret,
        audience=audience,
        algorithms=[algorithm],
    )

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    try:
        admin_id = UUID(str(subject))
    except ValueError as exc:  # pragma: no cover - defensive handling
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        ) from exc

    # Use shared DB user lookup helper with admin role requirement
    admin = await load_user_from_db(
        user_id=admin_id,
        session=db,
        require_active=True,
        require_role=UserRole.ADMIN,
    )

    permissions = payload.get("permissions", [])
    if not isinstance(permissions, list):
        permissions = []

    return AdminUser(
        id=admin.id, email=admin.email, full_name=admin.full_name, permissions=permissions
    )
