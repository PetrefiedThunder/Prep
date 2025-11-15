"""SevenShifts staffing API client."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.7shifts.com/v2"


class SevenShiftsError(RuntimeError):
    """Raised when the SevenShifts API returns an error response."""


@dataclass(slots=True)
class _AuthState:
    token: str
    expires_at: datetime

    def is_expired(self, *, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        return now >= self.expires_at


class SevenShiftsClient:
    """Minimal client for retrieving shift schedules from SevenShifts."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        session: requests.Session | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._auth: _AuthState | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch_schedules(
        self,
        *,
        start: datetime,
        end: datetime,
        location_id: str | None = None,
        per_page: int = 50,
    ) -> list[dict[str, Any]]:
        """Return all shifts between ``start`` and ``end`` inclusive."""

        return list(
            self.iter_schedules(start=start, end=end, location_id=location_id, per_page=per_page)
        )

    def iter_schedules(
        self,
        *,
        start: datetime,
        end: datetime,
        location_id: str | None = None,
        per_page: int = 50,
    ) -> Iterator[dict[str, Any]]:
        """Yield schedules using cursor-based pagination."""

        params: dict[str, Any] = {
            "start": self._format_datetime(start),
            "end": self._format_datetime(end),
            "per_page": per_page,
        }
        if location_id:
            params["location_id"] = location_id

        cursor: str | None = None

        while True:
            query = dict(params)
            if cursor:
                query["cursor"] = cursor

            response = self._request("get", "/schedules/shifts", params=query)
            payload = self._parse_json(response)

            data = self._extract_items(payload)
            yield from data

            cursor = self._next_cursor(payload)
            if not cursor:
                break

    # ------------------------------------------------------------------
    # Internal helpers
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
            json={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            timeout=30,
        )
        if response.status_code >= 400:
            raise SevenShiftsError(
                f"SevenShifts authentication failed with status {response.status_code}: {response.text}"
            )

        payload = self._parse_json(response)
        token = payload.get("access_token")
        expires_in = payload.get("expires_in", 3600)
        if not token:
            raise SevenShiftsError("SevenShifts authentication response missing access_token")

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
            raise SevenShiftsError("Unable to authenticate with SevenShifts")

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
            logger.info("SevenShifts token expired; re-authenticating")
            self._auth = None
            self._ensure_auth()
            if self._auth is None:
                raise SevenShiftsError("Failed to refresh SevenShifts authentication token")
            headers["Authorization"] = f"Bearer {self._auth.token}"
            response = self._session.request(
                method,
                self._resolve_url(path),
                headers=headers,
                timeout=30,
                **kwargs,
            )

        if response.status_code >= 400:
            raise SevenShiftsError(
                f"SevenShifts request failed with status {response.status_code}: {response.text}"
            )

        return response

    def _resolve_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return value.isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_json(response: requests.Response) -> dict[str, Any]:
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise SevenShiftsError("SevenShifts returned invalid JSON") from exc

    @staticmethod
    def _extract_items(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
        if "data" in payload and isinstance(payload["data"], list):
            return payload["data"]
        if "shifts" in payload and isinstance(payload["shifts"], list):
            return payload["shifts"]
        return []

    @staticmethod
    def _next_cursor(payload: dict[str, Any]) -> str | None:
        pagination = payload.get("pagination") or {}
        cursor = pagination.get("next_cursor") or pagination.get("next")
        if cursor:
            return str(cursor)
        return None


__all__ = ["SevenShiftsClient", "SevenShiftsError"]
