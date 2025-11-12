from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import httpx
from httpx import AsyncClient, MockTransport

from libs.rcs_client import RCSClient


def test_client_set_get_and_stream() -> None:
    async def _run() -> None:
        state: dict[str, dict[str, Any]] = {}
        version = 0
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal version
            path = request.url.path
            if request.method == "PUT" and path.startswith("/configs/"):
                payload = json.loads(request.content.decode("utf-8"))
                key = payload["key"]
                version += 1
                record = {
                    **payload,
                    "version": version,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                state[key] = record
                await event_queue.put(
                    {
                        "type": "upsert",
                        "key": key,
                        "version": version,
                        "emitted_at": datetime.now(UTC).isoformat(),
                        "config": record,
                    }
                )
                return httpx.Response(200, json=record)

            if (
                request.method == "GET"
                and path.startswith("/configs/")
                and path != "/configs/stream"
            ):
                key = path.split("/", 2)[-1]
                record = state.get(key)
                if record is None:
                    return httpx.Response(404, json={"detail": "not found"})
                return httpx.Response(200, json=record)

            if request.method == "GET" and path == "/configs":
                return httpx.Response(200, json=list(state.values()))

            if request.method == "GET" and path == "/configs/stream":
                snapshot = {
                    "type": "snapshot",
                    "emitted_at": datetime.now(UTC).isoformat(),
                    "configs": list(state.values()),
                }
                update = await event_queue.get()
                body = _encode_event(snapshot) + _encode_event(update)
                return httpx.Response(
                    200,
                    content=body,
                    headers={"content-type": "text/event-stream"},
                )

            return httpx.Response(404, json={"detail": "not found"})

        transport = MockTransport(handler)
        async with AsyncClient(
            transport=transport, base_url="http://testserver", trust_env=False
        ) as async_client:
            client = RCSClient(base_url="http://testserver", client=async_client)

            payload = {
                "key": "delivery.unified-tracker",
                "state": "on",
                "targeting": {"tenant_allowlist": ["kitchen_102"]},
            }

            stream = client.stream_configs()

            async def read_first_update() -> dict[str, Any]:
                async for event in stream:
                    if event["type"] == "snapshot":
                        continue
                    return event
                raise AssertionError("stream completed without update")

            waiter = asyncio.create_task(read_first_update())

            stored = await client.set_config(payload)
            assert stored["key"] == payload["key"]

            fetched = await client.get_config(payload["key"])
            assert fetched is not None
            assert fetched["key"] == payload["key"]

            update_event = await asyncio.wait_for(waiter, timeout=2.0)
            assert update_event["type"] == "upsert"
            assert update_event["config"]["state"] == "on"

            await client.close()

    asyncio.run(_run())


def _encode_event(event: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(event)}\n\n".encode()
