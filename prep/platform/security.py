"""Security utilities for the Prep platform APIs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Dict

import jwt

from prep.models.orm import User
from prep.settings import Settings

_PBKDF2_ITERATIONS = 390000


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


def create_access_token(user: User, settings: Settings) -> tuple[str, datetime]:
    """Create a signed JWT for ``user``."""

    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: Dict[str, Any] = {
        "sub": str(user.id),
        "roles": [user.role.value],
        "exp": expire,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, expire


def serialize_session(user: User, expires_at: datetime) -> str:
    """Serialize session payload for Redis storage."""

    payload = {
        "user_id": str(user.id),
        "role": user.role.value,
        "expires_at": expires_at.isoformat(),
    }
    return json.dumps(payload)
