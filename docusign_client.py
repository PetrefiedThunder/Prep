"""Client utilities for interacting with the DocuSign eSignature API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import requests


class DocuSignError(RuntimeError):
    """Raised when the DocuSign API returns an unexpected response."""


@dataclass
class DocuSignClient:
    """Simple DocuSign API client for sending template-based envelopes.

    Parameters
    ----------
    base_url:
        The DocuSign REST API base URL. This should include the API version,
        e.g. ``https://account.docusign.com/restapi``.
    account_id:
        The DocuSign account identifier (a GUID) that envelopes will be sent
        from.
    access_token:
        OAuth access token with sufficient permissions to create envelopes and
        generate recipient views.
    session:
        Optional pre-configured :class:`requests.Session` instance. A new
        session will be created when omitted.
    """

    base_url: str
    account_id: str
    access_token: str
    session: Optional[requests.Session] = None

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()

    def send_template(
        self,
        *,
        template_id: str,
        signer_email: str,
        signer_name: Optional[str] = None,
        return_url: str,
        role_name: str = "signer",
        client_user_id: Optional[str] = None,
        ping_url: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Send a template-based envelope and return the envelope ID and signing URL.

        Parameters
        ----------
        template_id:
            The DocuSign template identifier to use for the envelope.
        signer_email:
            The email address for the signer.
        signer_name:
            Full name of the signer. Defaults to the provided email address
            when omitted.
        return_url:
            URL that DocuSign should redirect to after the recipient completes
            signing.
        role_name:
            Name of the template role that should be filled by the signer.
        client_user_id:
            Optional identifier used for embedded signing. When provided, it
            will be set on the template role and the subsequent recipient view
            request.
        ping_url:
            Optional URL that DocuSign should ping via an iframe during the
            signing ceremony.

        Returns
        -------
        Tuple[str, str]
            A tuple containing the created envelope's ID and the recipient
            signing URL.

        Raises
        ------
        DocuSignError
            If DocuSign returns a non-successful response or the response is
            missing expected fields.
        """

        signer_name = signer_name or signer_email

        envelope_id = self._create_envelope(
            template_id=template_id,
            signer_email=signer_email,
            signer_name=signer_name,
            role_name=role_name,
            client_user_id=client_user_id,
        )
        signing_url = self._create_recipient_view(
            envelope_id=envelope_id,
            signer_email=signer_email,
            signer_name=signer_name,
            return_url=return_url,
            client_user_id=client_user_id,
            ping_url=ping_url,
        )
        return envelope_id, signing_url

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _create_envelope(
        self,
        *,
        template_id: str,
        signer_email: str,
        signer_name: str,
        role_name: str,
        client_user_id: Optional[str],
    ) -> str:
        url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes"
        payload = {
            "templateId": template_id,
            "templateRoles": [
                self._build_template_role(
                    role_name=role_name,
                    signer_email=signer_email,
                    signer_name=signer_name,
                    client_user_id=client_user_id,
                )
            ],
            "status": "sent",
        }

        response = self._request("post", url, json=payload)
        envelope_id = response.get("envelopeId")
        if not envelope_id:
            raise DocuSignError("DocuSign response did not include an envelopeId")
        return envelope_id

    def _create_recipient_view(
        self,
        *,
        envelope_id: str,
        signer_email: str,
        signer_name: str,
        return_url: str,
        client_user_id: Optional[str],
        ping_url: Optional[str],
    ) -> str:
        url = (
            f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/"
            f"{envelope_id}/views/recipient"
        )

        payload = {
            "returnUrl": return_url,
            "email": signer_email,
            "userName": signer_name,
        }
        if client_user_id is not None:
            payload["clientUserId"] = client_user_id
        if ping_url is not None:
            payload["pingUrl"] = ping_url

        response = self._request("post", url, json=payload)
        signing_url = response.get("url")
        if not signing_url:
            raise DocuSignError("DocuSign response did not include a signing URL")
        return signing_url

    def _build_template_role(
        self,
        *,
        role_name: str,
        signer_email: str,
        signer_name: str,
        client_user_id: Optional[str],
    ) -> dict:
        role = {
            "roleName": role_name,
            "name": signer_name,
            "email": signer_email,
        }
        if client_user_id is not None:
            role["clientUserId"] = client_user_id
        return role

    def _request(self, method: str, url: str, **kwargs) -> dict:
        if self.session is None:
            self.session = requests.Session()

        headers = kwargs.pop("headers", {})
        headers.setdefault("Authorization", f"Bearer {self.access_token}")
        headers.setdefault("Content-Type", "application/json")

        response = self.session.request(method, url, headers=headers, **kwargs)
        if not response.ok:
            raise DocuSignError(
                "DocuSign API request failed with status "
                f"{response.status_code}: {response.text}"
            )

        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - network failure scenario
            raise DocuSignError("DocuSign API returned non-JSON response") from exc

