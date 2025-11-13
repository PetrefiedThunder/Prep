"""Insurance provider API integrations for policy verification."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .health_departments import BaseAPIClient, RegulatoryAPIError


class InsuranceAPIError(RegulatoryAPIError):
    """Raised when an insurance provider request fails."""


@dataclass(slots=True)
class PolicyVerificationResult:
    """Normalized response from an insurance provider verification request."""

    provider: str
    policy_number: str
    active: bool
    coverage: dict[str, Any]
    effective_date: datetime | None
    expiration_date: datetime | None
    raw: dict[str, Any]


@dataclass(slots=True)
class CertificateIssueResult:
    """Standardized payload describing an issued insurance certificate."""

    provider: str
    policy_number: str
    certificate_url: str
    issued_at: datetime
    expires_at: datetime | None
    insured_name: str | None
    reference_id: str | None
    raw: dict[str, Any]


class BaseInsuranceAPI(BaseAPIClient):
    """Common helpers shared by specific insurance provider API clients."""

    provider: str = ""
    default_base_url: str | None = None
    api_key_env: str | None = None
    base_url_env: str | None = None

    def __init__(
        self, *, base_url: str | None = None, api_key: str | None = None, timeout: int = 30
    ) -> None:
        super().__init__(timeout=timeout)
        self.base_url = base_url or self._load_env(self.base_url_env) or self.default_base_url
        self.api_key = api_key or self._load_env(self.api_key_env)

    @staticmethod
    def _load_env(key: str | None) -> str | None:
        if not key:
            return None
        return os.getenv(key)

    def _auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _require_configuration(self) -> None:
        if not self.base_url:
            raise InsuranceAPIError(
                f"Base URL not configured for {self.provider}. Set the {self.base_url_env or 'base_url'} environment variable."
            )

    async def verify_policy(
        self, policy_number: str
    ) -> PolicyVerificationResult:  # pragma: no cover - interface
        raise NotImplementedError

    def _build_result(
        self, policy_number: str, response: dict[str, Any]
    ) -> PolicyVerificationResult:
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

    async def issue_certificate(
        self, policy_number: str, *, insured_name: str, reference_id: str | None = None
    ) -> CertificateIssueResult:  # pragma: no cover - interface
        raise NotImplementedError

    def _build_certificate_result(
        self,
        policy_number: str,
        response: dict[str, Any],
        *,
        reference_id: str | None = None,
    ) -> CertificateIssueResult:
        issued_at = self._parse_datetime(response.get("issued_at")) or datetime.now(UTC)
        url = response.get("certificate_url") or response.get("download_url") or ""
        return CertificateIssueResult(
            provider=self.provider,
            policy_number=policy_number,
            certificate_url=url,
            issued_at=issued_at,
            expires_at=self._parse_datetime(response.get("expires_at")),
            insured_name=response.get("insured_name"),
            reference_id=reference_id,
            raw=response,
        )

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
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


class NextInsuranceAPI(BaseInsuranceAPI):
    provider = "next"
    default_base_url = "https://api.nextinsurance.com/commercial"
    api_key_env = "NEXT_INSURANCE_API_KEY"
    base_url_env = "NEXT_INSURANCE_API_URL"

    async def verify_policy(self, policy_number: str) -> PolicyVerificationResult:
        self._require_configuration()
        url = f"{self.base_url}/policies/{policy_number}"
        response = await self._fetch_json(url, headers=self._auth_headers())
        return self._build_result(policy_number, response)

    async def issue_certificate(
        self, policy_number: str, *, insured_name: str, reference_id: str | None = None
    ) -> CertificateIssueResult:
        self._require_configuration()
        url = f"{self.base_url}/policies/{policy_number}/certificates"
        payload = {"insured_name": insured_name, "reference_id": reference_id}
        response = await self._post_json(url, payload=payload, headers=self._auth_headers())
        return self._build_certificate_result(
            policy_number,
            response,
            reference_id=reference_id,
        )


class ThimbleAPI(BaseInsuranceAPI):
    provider = "thimble"
    default_base_url = "https://api.thimble.com/commercial"
    api_key_env = "THIMBLE_API_KEY"
    base_url_env = "THIMBLE_API_URL"

    async def verify_policy(self, policy_number: str) -> PolicyVerificationResult:
        self._require_configuration()
        url = f"{self.base_url}/policies/{policy_number}"
        response = await self._fetch_json(url, headers=self._auth_headers())
        return self._build_result(policy_number, response)

    async def issue_certificate(
        self, policy_number: str, *, insured_name: str, reference_id: str | None = None
    ) -> CertificateIssueResult:
        self._require_configuration()
        url = f"{self.base_url}/policies/{policy_number}/certificates"
        payload = {"insured_name": insured_name, "reference_id": reference_id}
        response = await self._post_json(url, payload=payload, headers=self._auth_headers())
        return self._build_certificate_result(
            policy_number,
            response,
            reference_id=reference_id,
        )


class InsuranceVerificationAPI:
    """Facade for verifying commercial insurance policies across providers."""

    def __init__(self, providers: dict[str, BaseInsuranceAPI] | None = None) -> None:
        self.providers = providers or {
            "state_farm": StateFarmAPI(),
            "allstate": AllStateAPI(),
            "liberty_mutual": LibertyMutualAPI(),
            "next": NextInsuranceAPI(),
            "thimble": ThimbleAPI(),
        }

    async def verify_coverage(self, provider: str, policy_number: str) -> PolicyVerificationResult:
        if provider not in self.providers:
            raise InsuranceAPIError(f"Unsupported insurance provider '{provider}'.")
        return await self.providers[provider].verify_policy(policy_number)

    async def issue_certificate(
        self,
        provider: str,
        policy_number: str,
        *,
        insured_name: str,
        reference_id: str | None = None,
    ) -> CertificateIssueResult:
        if provider not in self.providers:
            raise InsuranceAPIError(f"Unsupported insurance provider '{provider}'.")
        return await self.providers[provider].issue_certificate(
            policy_number,
            insured_name=insured_name,
            reference_id=reference_id,
        )


__all__ = [
    "InsuranceAPIError",
    "PolicyVerificationResult",
    "CertificateIssueResult",
    "StateFarmAPI",
    "AllStateAPI",
    "LibertyMutualAPI",
    "NextInsuranceAPI",
    "ThimbleAPI",
    "InsuranceVerificationAPI",
]
