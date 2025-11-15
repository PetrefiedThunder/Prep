"""Extensible authentication broker interfaces for third-party SSO providers."""

from __future__ import annotations

import base64
from collections.abc import Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
from defusedxml import ElementTree as ET
from pydantic import BaseModel, Field

from prep.models.orm import IdentityProvider, IdentityProviderType
from prep.settings import Settings


class AuthProviderError(RuntimeError):
    """Raised when an external identity provider interaction fails."""


class IdentityProfile(BaseModel):
    """Normalized identity information returned by an auth provider."""

    subject: str
    email: str | None = None
    full_name: str | None = Field(default=None, alias="name")
    claims: dict[str, Any] = Field(default_factory=dict)


@dataclass(slots=True)
class ProviderContext:
    """Runtime configuration shared across provider implementations."""

    provider: IdentityProvider
    settings: Settings


class BaseAuthProvider:
    """Abstract base class for authentication providers."""

    def __init__(
        self,
        context: ProviderContext,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._context = context
        self._client = client

    @property
    def provider(self) -> IdentityProvider:
        return self._context.provider

    @property
    def settings(self) -> Settings:
        return self._context.settings

    @asynccontextmanager
    async def _client_ctx(self) -> Iterable[httpx.AsyncClient]:
        if self._client is not None:
            yield self._client
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            yield client

    async def build_authorization_url(self, *, redirect_uri: str, state: str) -> str:
        raise NotImplementedError

    async def exchange_code(self, *, code: str, redirect_uri: str | None = None) -> IdentityProfile:
        raise NotImplementedError


class OIDCProvider(BaseAuthProvider):
    """OpenID Connect provider implementation."""

    async def build_authorization_url(self, *, redirect_uri: str, state: str) -> str:
        metadata = self.provider.metadata or {}
        authorization_endpoint = metadata.get("authorization_endpoint")
        client_id = (self.provider.settings or {}).get("client_id") or metadata.get("client_id")
        if not authorization_endpoint or not client_id:
            raise AuthProviderError("OIDC provider is missing authorization configuration")

        scope = metadata.get("scope", "openid email profile")
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
        }
        prompt = metadata.get("prompt")
        if prompt:
            params["prompt"] = prompt
        return f"{authorization_endpoint}?{urlencode(params)}"

    async def exchange_code(self, *, code: str, redirect_uri: str | None = None) -> IdentityProfile:
        metadata = self.provider.metadata or {}
        token_endpoint = metadata.get("token_endpoint")
        userinfo_endpoint = metadata.get("userinfo_endpoint")
        client_id = (self.provider.settings or {}).get("client_id") or metadata.get("client_id")
        client_secret = (self.provider.settings or {}).get("client_secret") or metadata.get(
            "client_secret"
        )

        if not token_endpoint or not client_id or not client_secret:
            raise AuthProviderError("OIDC provider is missing token endpoint configuration")
        if not userinfo_endpoint:
            raise AuthProviderError("OIDC provider is missing userinfo endpoint configuration")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if redirect_uri:
            data["redirect_uri"] = redirect_uri

        async with self._client_ctx() as client:
            token_response = await client.post(
                token_endpoint, data=data, headers={"Accept": "application/json"}
            )
            token_response.raise_for_status()
            token_payload = token_response.json()

        access_token = token_payload.get("access_token")
        if not access_token:
            raise AuthProviderError("OIDC token endpoint did not return an access token")

        async with self._client_ctx() as client:
            userinfo_response = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )
            userinfo_response.raise_for_status()
            profile_payload = userinfo_response.json()

        subject = profile_payload.get("sub") or token_payload.get("id_token")
        if not subject:
            raise AuthProviderError("OIDC provider response did not include a subject claim")

        return IdentityProfile(
            subject=str(subject),
            email=profile_payload.get("email"),
            full_name=profile_payload.get("name"),
            claims=profile_payload,
        )


class SAMLProvider(BaseAuthProvider):
    """SAML 2.0 provider implementation."""

    async def build_authorization_url(self, *, redirect_uri: str, state: str) -> str:
        metadata = self.provider.metadata or {}
        sso_url = metadata.get("sso_url") or metadata.get("single_sign_on_service")
        if not sso_url:
            raise AuthProviderError("SAML provider is missing an SSO endpoint")
        return f"{sso_url}?{urlencode({'RelayState': state, 'ReturnTo': redirect_uri})}"

    async def exchange_code(self, *, code: str, redirect_uri: str | None = None) -> IdentityProfile:
        try:
            decoded = base64.b64decode(code)
        except (TypeError, ValueError) as exc:
            raise AuthProviderError("Invalid SAML response payload") from exc

        try:
            document = decoded.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AuthProviderError("SAML assertion is not valid UTF-8") from exc

        attributes = self._extract_attributes(document)
        subject = attributes.get("name_id") or attributes.get("sub")
        if not subject:
            raise AuthProviderError("SAML response did not include a subject identifier")

        return IdentityProfile(
            subject=str(subject),
            email=attributes.get("email"),
            full_name=attributes.get("full_name") or attributes.get("display_name"),
            claims=attributes,
        )

    @staticmethod
    def _extract_attributes(document: str) -> dict[str, Any]:
        """Very small helper to parse common SAML attributes from an XML document."""

        try:
            root = ET.fromstring(document)
        except ET.ParseError as exc:
            raise AuthProviderError("Unable to parse SAML response") from exc

        ns = {
            "saml2": "urn:oasis:names:tc:SAML:2.0:assertion",
        }
        attributes: dict[str, Any] = {}
        name_id = root.find(".//saml2:Subject/saml2:NameID", ns)
        if name_id is not None and name_id.text:
            attributes["name_id"] = name_id.text

        for attribute in root.findall(".//saml2:Attribute", ns):
            name = attribute.attrib.get("Name")
            if not name:
                continue
            values = [
                value.text for value in attribute.findall("saml2:AttributeValue", ns) if value.text
            ]
            if not values:
                continue
            if len(values) == 1:
                attributes[name] = values[0]
            else:
                attributes[name] = values

        return attributes


class ProviderRegistry:
    """Factory for instantiating auth providers from ORM records."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def load(
        self, provider: IdentityProvider, *, client: httpx.AsyncClient | None = None
    ) -> BaseAuthProvider:
        if not provider.is_active:
            raise AuthProviderError("Identity provider is disabled")
        context = ProviderContext(provider=provider, settings=self._settings)
        if provider.provider_type is IdentityProviderType.OIDC:
            return OIDCProvider(context, client=client)
        if provider.provider_type is IdentityProviderType.SAML:
            return SAMLProvider(context, client=client)
        raise AuthProviderError(f"Unsupported identity provider type: {provider.provider_type}")


__all__ = [
    "AuthProviderError",
    "IdentityProfile",
    "BaseAuthProvider",
    "OIDCProvider",
    "SAMLProvider",
    "ProviderRegistry",
]

"""Identity provider broker implementations for the Prep platform."""

from .base import IdentityAssertion
from .oidc import OIDCBroker
from .saml import SAMLIdentityBroker

__all__ = ["IdentityAssertion", "OIDCBroker", "SAMLIdentityBroker"]
