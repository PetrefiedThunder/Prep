"""Async client for the Realtime Config Service."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx


class RCSClient:
    """Convenience wrapper around the RCS HTTP API."""

    def __init__(
        self,
        base_url: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float | None = 10.0,
        stream_transport_factory: Callable[[], httpx.AsyncBaseTransport] | None = None,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            trust_env=False,
        )
        self._owns_client = client is None
        self._base_url = base_url
        self._stream_transport_factory = stream_transport_factory

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_config(self, key: str) -> dict[str, Any] | None:
        response = await self._client.get(f"/configs/{key}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def set_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        key = payload.get("key")
        if not key:
            raise ValueError("Configuration payload must include a 'key' field")
        response = await self._client.put(f"/configs/{key}", json=payload)
        response.raise_for_status()
        return response.json()

    async def delete_config(self, key: str) -> None:
        response = await self._client.delete(f"/configs/{key}")
        if response.status_code not in (200, 204):
            response.raise_for_status()

    async def list_configs(self, prefix: str | None = None) -> list[dict[str, Any]]:
        params = {"prefix": prefix} if prefix else None
        response = await self._client.get("/configs", params=params)
        response.raise_for_status()
        return response.json()

    async def stream_configs(self, *, prefix: str | None = None) -> AsyncIterator[dict[str, Any]]:
        params = {"prefix": prefix} if prefix else None
        stream_client = self._client
        owns_stream_client = False
        if self._stream_transport_factory is not None:
            stream_client = httpx.AsyncClient(
                transport=self._stream_transport_factory(),
                base_url=self._base_url,
                trust_env=False,
                timeout=httpx.Timeout(60.0, connect=10.0),  # 60s total, 10s connect
            )
            owns_stream_client = True

        try:
            async with stream_client.stream("GET", "/configs/stream", params=params) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if not line.startswith("data: "):
                        continue
                    payload = json.loads(line[6:])
                    yield payload
        finally:
            if owns_stream_client:
                await stream_client.aclose()

    async def __aenter__(self) -> RCSClient:
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()
