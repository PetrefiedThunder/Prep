"""Polling job for synchronizing cook/prep metrics from the QSR Automations API."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence

import httpx

from apps.scheduling.metrics import trigger_scheduling_recalculation
from modules.kitchen_metrics.models import KitchenMetric, KitchenMetricsService, get_default_kitchen_metrics_service

logger = logging.getLogger(__name__)

Fetcher = Callable[[], Sequence[Mapping[str, Any]]]


class QSRClientError(RuntimeError):
    """Raised when the QSR Automations API cannot be reached or returns an error."""


@dataclass(slots=True)
class QSRClient:
    """Minimal synchronous client for retrieving cook and prep durations."""

    base_url: str
    api_key: str | None = None
    timeout: float = 10.0

    METRICS_PATH = "/automations/metrics"

    @classmethod
    def from_environment(cls) -> "QSRClient":
        """Build a client from environment variables."""

        base_url = os.getenv("QSR_AUTOMATIONS_BASE_URL")
        if not base_url:
            raise QSRClientError("QSR_AUTOMATIONS_BASE_URL is not configured")
        api_key = os.getenv("QSR_AUTOMATIONS_API_KEY")
        timeout_str = os.getenv("QSR_AUTOMATIONS_TIMEOUT", "10.0")
        try:
            timeout = float(timeout_str)
        except ValueError:  # pragma: no cover - defensive guard
            timeout = 10.0
        return cls(base_url=base_url.rstrip("/"), api_key=api_key, timeout=timeout)

    def fetch_metrics(self) -> list[Mapping[str, Any]]:
        """Fetch cook and prep durations for all linked locations."""

        url = f"{self.base_url}{self.METRICS_PATH}"
        headers: MutableMapping[str, str] = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:  # pragma: no cover - network failure path
            logger.warning("Failed to fetch QSR automations metrics", exc_info=exc, extra={"url": url})
            raise QSRClientError("Unable to fetch QSR automations metrics") from exc

        if isinstance(data, Mapping):
            # Some deployments wrap the list under a top-level key such as "locations".
            if "locations" in data and isinstance(data["locations"], Sequence):
                return list(data["locations"])
            if "data" in data and isinstance(data["data"], Sequence):
                return list(data["data"])
        if isinstance(data, Sequence):
            return list(data)
        raise QSRClientError("Unexpected payload received from QSR Automations API")


def _parse_timestamp(value: Any) -> datetime:
    """Best-effort parsing of timestamps from the QSR payload."""

    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            timestamp = datetime.fromisoformat(normalized)
        except ValueError:
            logger.debug("Falling back to current time for malformed timestamp", extra={"value": value})
            timestamp = datetime.now(timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _coerce_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_location(payload: Mapping[str, Any]) -> KitchenMetric:
    location = payload.get("location_id") or payload.get("locationId") or payload.get("store_id")
    if not location:
        raise QSRClientError("QSR payload missing location identifier")

    timestamp = _parse_timestamp(
        payload.get("collected_at")
        or payload.get("timestamp")
        or payload.get("updated_at")
        or payload.get("reported_at")
    )

    prep_seconds = _coerce_int(
        payload.get("prep_duration_seconds")
        or payload.get("prepSeconds")
        or payload.get("prep_time_seconds")
        or payload.get("prep_time")
    )
    cook_seconds = _coerce_int(
        payload.get("cook_duration_seconds")
        or payload.get("cookSeconds")
        or payload.get("cook_time_seconds")
        or payload.get("cook_time")
    )

    return KitchenMetric(
        location_id=str(location),
        collected_at=timestamp,
        prep_duration_seconds=max(prep_seconds, 0),
        cook_duration_seconds=max(cook_seconds, 0),
    )


def normalize_qsr_metrics(payload: Iterable[Mapping[str, Any]]) -> list[KitchenMetric]:
    """Normalize raw QSR payloads into :class:`KitchenMetric` records."""

    metrics: list[KitchenMetric] = []
    for item in payload:
        try:
            metrics.append(_normalize_location(item))
        except QSRClientError as exc:
            logger.warning("Skipping QSR payload", extra={"error": str(exc), "payload": item})
    return metrics


def sync_qsr_automations_metrics(
    *,
    fetcher: Fetcher | None = None,
    client: QSRClient | None = None,
    service: KitchenMetricsService | None = None,
) -> list[KitchenMetric]:
    """Fetch, normalize, and persist metrics, then refresh scheduling dashboards."""

    if fetcher is None:
        if client is None:
            client = QSRClient.from_environment()
        fetcher = client.fetch_metrics

    service = service or get_default_kitchen_metrics_service()

    raw_metrics = fetcher()
    normalized_metrics = normalize_qsr_metrics(raw_metrics)
    persisted = service.record_metrics(normalized_metrics)

    trigger_scheduling_recalculation(service, metrics=persisted)

    logger.info(
        "Synchronized QSR automations metrics",
        extra={"count": len(persisted)},
    )
    return persisted


__all__ = [
    "QSRClient",
    "QSRClientError",
    "normalize_qsr_metrics",
    "sync_qsr_automations_metrics",
]
