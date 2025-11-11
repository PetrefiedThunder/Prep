"""JSON Web Token helpers."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

# SECURITY FIX: Require JWT secret from environment, no insecure defaults
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "your-secret-key":
    raise ValueError(
        "JWT_SECRET_KEY environment variable must be set to a strong secret value. "
        "Never use default or weak secrets in production."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict) -> str:
    """Create a signed JWT access token.

    SECURITY: Uses timezone-aware datetime to prevent clock skew issues.
    """
    to_encode = data.copy()
    # SECURITY FIX: Use datetime.now(UTC) instead of deprecated datetime.utcnow()
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> dict | None:
    """Verify a JWT access token and return its payload if valid."""

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


__all__ = [
    "create_access_token",
    "verify_access_token",
]
