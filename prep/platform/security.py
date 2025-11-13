"""Security utilities for the Prep platform APIs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from prep.models.orm import User, UserRole
from prep.settings import Settings

_PBKDF2_ITERATIONS = 390000
_API_KEY_PREFIX_BYTES = 4
_API_KEY_TOKEN_BYTES = 32


def _derive_key(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)


def hash_password(password: str) -> str:
    """Hash ``password`` using PBKDF2."""

    salt = secrets.token_bytes(16)
    dk = _derive_key(password, salt)
    return "$".join(
        [
            base64.b64encode(salt).decode("ascii"),
            str(_PBKDF2_ITERATIONS),
            base64.b64encode(dk).decode("ascii"),
        ]
    )


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify ``password`` against a PBKDF2 hash."""

    try:
        salt_b64, iterations_str, hash_b64 = hashed_password.split("$")
    except ValueError:
        return False

    try:
        salt = base64.b64decode(salt_b64)
        iterations = int(iterations_str)
        expected = base64.b64decode(hash_b64)
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def create_access_token(
    user: User,
    settings: Settings,
    *,
    roles: Iterable[str] | None = None,
) -> tuple[str, datetime]:
    """Create a signed JWT for ``user``."""

    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    derived_roles = list(roles or [])
    if not derived_roles:
        derived_roles.append(user.role.value)
        if user.is_admin and UserRole.ADMIN.value not in derived_roles:
            derived_roles.append(UserRole.ADMIN.value)

    payload: dict[str, Any] = {
        "sub": str(user.id),
        "roles": _collect_roles(user),
        "roles": derived_roles,
        "exp": expire,
        "iss": settings.oidc_issuer or "prep-platform",
        "aud": settings.oidc_audience or settings.oidc_client_id,
    }
    signing_key = settings.auth_signing_key or settings.secret_key
    token = jwt.encode(payload, signing_key, algorithm="HS256")
    return token, expire


def create_refresh_token(settings: Settings) -> tuple[str, datetime]:
    """Create an opaque refresh token string and its expiry timestamp."""

    token = secrets.token_urlsafe(48)
    expire = datetime.now(UTC) + timedelta(seconds=settings.refresh_token_ttl_seconds)
    return token, expire


def hash_token(value: str) -> str:
    """Return a stable hash for storing opaque tokens."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_api_key_secret() -> tuple[str, str]:
    """Generate an API key prefix and full secret."""

    prefix = secrets.token_hex(_API_KEY_PREFIX_BYTES)
    secret = secrets.token_urlsafe(_API_KEY_TOKEN_BYTES)
    return prefix, f"{prefix}.{secret}"


def hash_api_key_secret(value: str) -> str:
    """Hash an API key for persistence."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def serialize_session(user: User, expires_at: datetime) -> str:
    """Serialize session payload for Redis storage."""

    payload = {
        "user_id": str(user.id),
        "role": user.role.value,
        "roles": _collect_roles(user),
        "roles": [user.role.value],
        "expires_at": expires_at.isoformat(),
    }
    return json.dumps(payload)


def hash_token(token: str) -> str:
    """Return a deterministic hash for sensitive token strings."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_refresh_token() -> str:
    """Generate a high-entropy refresh token."""

    return secrets.token_urlsafe(48)


def generate_api_key() -> tuple[str, str, str]:
    """Return a tuple of (raw_key, prefix, hashed_key)."""

    raw = secrets.token_urlsafe(48)
    prefix = raw[:12]
    return raw, prefix, hash_token(raw)


def _collect_roles(user: User) -> list[str]:
    roles = {user.role.value}
    extra_roles = getattr(user, "rbac_roles", None)
    if isinstance(extra_roles, list):
        for role in extra_roles:
            if isinstance(role, str) and role.strip():
                roles.add(role.strip())
    return sorted(roles)
