"""Deputy staffing API client."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://app.deputy.com/api/v1"


class DeputyError(RuntimeError):
    """Raised when the Deputy API returns an error response."""


@dataclass(slots=True)
class _AuthState:
    token: str
    expires_at: datetime

    def is_expired(self, *, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        return now >= self.expires_at


class DeputyClient:
    """Client for retrieving roster information from Deputy."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        base_url: str = DEFAULT_BASE_URL,
        session: requests.Session | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._auth: _AuthState | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch_shifts(
        self,
        *,
        start: datetime,
        end: datetime,
        location_id: str | None = None,
        page_size: int = 200,
    ) -> list[dict[str, Any]]:
        """Return roster entries between ``start`` and ``end`` inclusive."""

        return list(
            self.iter_shifts(start=start, end=end, location_id=location_id, page_size=page_size)
        )

    def iter_shifts(
        self,
        *,
        start: datetime,
        end: datetime,
        location_id: str | None = None,
        page_size: int = 200,
    ) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {
            "start": self._format_datetime(start),
            "end": self._format_datetime(end),
            "page_size": page_size,
            "offset": 0,
        }
        if location_id:
            params["location_id"] = location_id

        while True:
            response = self._request("get", "/roster", params=params)
            payload = self._parse_json(response)

            data = self._extract_items(payload)
            for item in data:
                yield item

            next_offset = self._next_offset(payload, params["offset"], len(data), page_size)
            if next_offset is None:
                break
            params["offset"] = next_offset

    # ------------------------------------------------------------------
    # Authentication and helpers
    # ------------------------------------------------------------------
    def _ensure_auth(self) -> None:
        if self._auth and not self._auth.is_expired():
            return

        token, expires_in = self._authenticate()
        expires_at = datetime.now(UTC) + timedelta(seconds=max(0, expires_in - 30))
        self._auth = _AuthState(token=token, expires_at=expires_at)

    def _authenticate(self) -> tuple[str, int]:
        response = self._session.request(
            "post",
            f"{self.base_url}/oauth/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            timeout=30,
        )
        if response.status_code >= 400:
            raise DeputyError(
                f"Deputy authentication failed with status {response.status_code}: {response.text}"
            )

        payload = self._parse_json(response)
        token = payload.get("access_token")
        expires_in = payload.get("expires_in", 3600)
        if not token:
            raise DeputyError("Deputy authentication response missing access_token")

        return str(token), int(expires_in)

    def _request(
        self,
        method: str,
        path: str,
        *,
        retry: bool = True,
        **kwargs: Any,
    ) -> requests.Response:
        self._ensure_auth()

        if self._auth is None:
            raise DeputyError("Unable to authenticate with Deputy")

        headers = dict(kwargs.pop("headers", {}))
        headers.setdefault("Authorization", f"Bearer {self._auth.token}")
        headers.setdefault("Accept", "application/json")

        response = self._session.request(
            method,
            self._resolve_url(path),
            headers=headers,
            timeout=30,
            **kwargs,
        )

        if response.status_code == 401 and retry:
            logger.info("Deputy token expired; re-authenticating")
            self._auth = None
            self._ensure_auth()
            if self._auth is None:
                raise DeputyError("Failed to refresh Deputy authentication token")
            headers["Authorization"] = f"Bearer {self._auth.token}"
            response = self._session.request(
                method,
                self._resolve_url(path),
                headers=headers,
                timeout=30,
                **kwargs,
            )

        if response.status_code >= 400:
            raise DeputyError(
                f"Deputy request failed with status {response.status_code}: {response.text}"
            )

        return response

    def _resolve_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    @staticmethod
    def _parse_json(response: requests.Response) -> dict[str, Any]:
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise DeputyError("Deputy returned invalid JSON") from exc

    @staticmethod
    def _extract_items(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
        if "data" in payload and isinstance(payload["data"], list):
            return payload["data"]
        if "results" in payload and isinstance(payload["results"], list):
            return payload["results"]
        return []

    @staticmethod
    def _next_offset(
        payload: dict[str, Any],
        current_offset: int,
        returned: int,
        page_size: int,
    ) -> int | None:
        pagination = payload.get("pagination") or payload.get("meta") or {}
        if "next_offset" in pagination:
            return int(pagination["next_offset"])

        if returned < page_size:
            return None

        return current_offset + page_size

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        else:
            value = value.astimezone(UTC)
        return value.isoformat().replace("+00:00", "Z")


__all__ = ["DeputyClient", "DeputyError"]
