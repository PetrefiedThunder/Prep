"""OIDC identity broker for Prep."""

from __future__ import annotations

from typing import Any

import jwt
from jwt import PyJWKClient

from prep.settings import Settings

from .base import IdentityAssertion


class OIDCBroker:
    """Minimal OpenID Connect helper to validate ID tokens."""

    def __init__(self, settings: Settings) -> None:
        self._issuer = settings.oidc_issuer
        self._audience = settings.oidc_audience or settings.oidc_client_id
        self._signing_key = settings.auth_signing_key or settings.secret_key
        self._jwks_client: PyJWKClient | None = None
        self._algorithms = ("RS256", "HS256")

        if settings.oidc_jwks_url:
            try:
                self._jwks_client = PyJWKClient(str(settings.oidc_jwks_url))
            except Exception:  # pragma: no cover - defensive guard
                self._jwks_client = None

    def verify(self, id_token: str) -> IdentityAssertion:
        """Validate ``id_token`` and normalize it into an :class:`IdentityAssertion`."""

        key: Any
        if self._jwks_client is not None:
            key = self._jwks_client.get_signing_key_from_jwt(id_token).key
        else:
            key = self._signing_key

        payload = jwt.decode(
            id_token,
            key,
            algorithms=self._algorithms,
            audience=self._audience,
            issuer=self._issuer,
            options={"require": ["sub"]},
        )

        if not isinstance(payload, dict):  # pragma: no cover - defensive programming
            raise ValueError("ID token payload is not a mapping")

        return IdentityAssertion(
            subject=str(payload["sub"]),
            email=payload.get("email"),
            full_name=payload.get("name"),
            attributes=payload,
        )


__all__ = ["OIDCBroker"]
