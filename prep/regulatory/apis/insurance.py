"""Insurance provider API integrations for policy verification."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from .health_departments import BaseAPIClient, RegulatoryAPIError


class InsuranceAPIError(RegulatoryAPIError):
    """Raised when an insurance provider request fails."""


@dataclass(slots=True)
class PolicyVerificationResult:
    """Normalized response from an insurance provider verification request."""

    provider: str
    policy_number: str
    active: bool
    coverage: Dict[str, Any]
    effective_date: Optional[datetime]
    expiration_date: Optional[datetime]
    raw: Dict[str, Any]


class BaseInsuranceAPI(BaseAPIClient):
    """Common helpers shared by specific insurance provider API clients."""

    provider: str = ""
    default_base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    base_url_env: Optional[str] = None

    def __init__(self, *, base_url: Optional[str] = None, api_key: Optional[str] = None, timeout: int = 30) -> None:
        super().__init__(timeout=timeout)
        self.base_url = base_url or self._load_env(self.base_url_env) or self.default_base_url
        self.api_key = api_key or self._load_env(self.api_key_env)

    @staticmethod
    def _load_env(key: Optional[str]) -> Optional[str]:
        if not key:
            return None
        return os.getenv(key)

    def _auth_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _require_configuration(self) -> None:
        if not self.base_url:
            raise InsuranceAPIError(
                f"Base URL not configured for {self.provider}. Set the {self.base_url_env or 'base_url'} environment variable."
            )

    async def verify_policy(self, policy_number: str) -> PolicyVerificationResult:  # pragma: no cover - interface
        raise NotImplementedError

    def _build_result(self, policy_number: str, response: Dict[str, Any]) -> PolicyVerificationResult:
        coverage = response.get("coverage") or {}
        return PolicyVerificationResult(
            provider=self.provider,
            policy_number=policy_number,
            active=bool(response.get("active", False)),
            coverage=coverage,
            effective_date=self._parse_datetime(response.get("effective_date")),
            expiration_date=self._parse_datetime(response.get("expiration_date")),
            raw=response,
        )

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None


class StateFarmAPI(BaseInsuranceAPI):
    provider = "state_farm"
    default_base_url = "https://api.statefarm.com/commercial"
    api_key_env = "STATE_FARM_API_KEY"
    base_url_env = "STATE_FARM_API_URL"

    async def verify_policy(self, policy_number: str) -> PolicyVerificationResult:
        self._require_configuration()
        url = f"{self.base_url}/policies/{policy_number}"
        response = await self._fetch_json(url, headers=self._auth_headers())
        return self._build_result(policy_number, response)


class AllStateAPI(BaseInsuranceAPI):
    provider = "allstate"
    default_base_url = "https://api.allstate.com/commercial"
    api_key_env = "ALLSTATE_API_KEY"
    base_url_env = "ALLSTATE_API_URL"

    async def verify_policy(self, policy_number: str) -> PolicyVerificationResult:
        self._require_configuration()
        url = f"{self.base_url}/policies/{policy_number}/verification"
        response = await self._fetch_json(url, headers=self._auth_headers())
        return self._build_result(policy_number, response)


class LibertyMutualAPI(BaseInsuranceAPI):
    provider = "liberty_mutual"
    default_base_url = "https://api.libertymutual.com/commercial"
    api_key_env = "LIBERTY_MUTUAL_API_KEY"
    base_url_env = "LIBERTY_MUTUAL_API_URL"

    async def verify_policy(self, policy_number: str) -> PolicyVerificationResult:
        self._require_configuration()
        url = f"{self.base_url}/policies/{policy_number}/status"
        response = await self._fetch_json(url, headers=self._auth_headers())
        return self._build_result(policy_number, response)


class InsuranceVerificationAPI:
    """Facade for verifying commercial insurance policies across providers."""

    def __init__(self, providers: Optional[Dict[str, BaseInsuranceAPI]] = None) -> None:
        self.providers = providers or {
            "state_farm": StateFarmAPI(),
            "allstate": AllStateAPI(),
            "liberty_mutual": LibertyMutualAPI(),
        }

    async def verify_coverage(self, provider: str, policy_number: str) -> PolicyVerificationResult:
        if provider not in self.providers:
            raise InsuranceAPIError(f"Unsupported insurance provider '{provider}'.")
        return await self.providers[provider].verify_policy(policy_number)


__all__ = [
    "InsuranceAPIError",
    "PolicyVerificationResult",
    "StateFarmAPI",
    "AllStateAPI",
    "LibertyMutualAPI",
    "InsuranceVerificationAPI",
]
