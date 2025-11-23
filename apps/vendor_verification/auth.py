"""Authentication middleware for the Vendor Verification API."""

from __future__ import annotations

import hashlib
from argon2 import PasswordHasher

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from apps.vendor_verification.models import ErrorResponse
from apps.vendor_verification.orm_models import Tenant


async def get_api_key(x_prep_api_key: str = Header(..., alias="X-Prep-Api-Key")) -> str:
    """Extract API key from header."""
    return x_prep_api_key


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage/comparison."""
    hasher = PasswordHasher()
    return hasher.hash(api_key)


async def get_current_tenant(
    api_key: str = Depends(get_api_key),
    db: Session = None,
) -> Tenant:
    """
    Authenticate request and return current tenant.

    Args:
        api_key: API key from header
        db: Database session (injected as dependency)

    Returns:
        Tenant object

    Raises:
        HTTPException: 401 if authentication fails
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                code="internal_error",
                message="Database session not available",
            ).model_dump(),
        )

    api_key_hash = hash_api_key(api_key)

    tenant = db.query(Tenant).filter(Tenant.api_key_hash == api_key_hash).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                code="unauthorized",
                message="Invalid or missing API key",
            ).model_dump(),
        )

    return tenant


class TenantContext:
    """Request context holding authenticated tenant."""

    def __init__(self):
        self.tenant_id: str | None = None


def get_tenant_context(request: Request) -> TenantContext:
    """Get or create tenant context from request state."""
    if not hasattr(request.state, "tenant_context"):
        request.state.tenant_context = TenantContext()
    return request.state.tenant_context
