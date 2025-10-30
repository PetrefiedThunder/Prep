from __future__ import annotations
import asyncio
import json
import sys
import types
from pathlib import Path
from typing import Dict, List

from httpx import ASGITransport, AsyncClient

if "boto3" not in sys.modules:
    boto3_stub = types.ModuleType("boto3")
    boto3_stub.client = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    sys.modules["boto3"] = boto3_stub

if "botocore.client" not in sys.modules:
    botocore_client = types.ModuleType("botocore.client")

    class _BaseClient:  # pragma: no cover - simple stub
        ...

    botocore_client.BaseClient = _BaseClient  # type: ignore[attr-defined]
    sys.modules["botocore.client"] = botocore_client

if "prep.platform" not in sys.modules:
    platform_pkg = types.ModuleType("prep.platform")
    platform_pkg.__path__ = [
        str((Path(__file__).resolve().parents[2] / "prep" / "platform"))
    ]
    sys.modules["prep.platform"] = platform_pkg

from prep.platform.rcs.service import create_app
from prep.platform.rcs.storage import ConfigStore


def test_upsert_and_fetch_config() -> None:
    async def _run() -> None:
        app = create_app(ConfigStore())
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            trust_env=False,
        ) as client:
            payload = _sample_entry()
            response = await client.put(f"/configs/{payload['key']}", json=payload)
            assert response.status_code == 200, response.text
            stored = response.json()
            assert stored["key"] == payload["key"]
            assert stored["state"] == "on"
            assert stored["rollout"]["strategy"] == "canary"

            response = await client.get(f"/configs/{payload['key']}")
            assert response.status_code == 200
            fetched = response.json()
            assert fetched["version"] == stored["version"]

    asyncio.run(_run())


def test_stream_includes_snapshot_and_updates() -> None:
    async def _run() -> None:
        store = ConfigStore()
        app = create_app(store)
        messages: List[Dict[str, object]] = []

        queue: asyncio.Queue[Dict[str, object]] = asyncio.Queue()
        await queue.put({"type": "http.request", "body": b"", "more_body": False})

        async def receive() -> Dict[str, object]:
            return await queue.get()

        async def send(message: Dict[str, object]) -> None:
            messages.append(message)

        stream_task = asyncio.create_task(
            app._handle_stream({}, receive, send)
        )

        await asyncio.sleep(0)

        payload = _sample_entry()
        await store.upsert(_entry_model(payload))

        await asyncio.sleep(0)
        await queue.put({"type": "http.disconnect"})
        await stream_task

        assert messages[0]["status"] == 200
        snapshot_event = _decode_event(messages[1]["body"])
        assert snapshot_event["type"] == "snapshot"
        assert snapshot_event["configs"] == []

        update_event = _decode_event(messages[2]["body"])
        assert update_event["type"] == "upsert"
        assert update_event["config"]["key"] == payload["key"]

    asyncio.run(_run())


def _sample_entry(key: str = "delivery.unified-tracker") -> Dict[str, object]:
    return {
        "key": key,
        "state": "on",
        "targeting": {"tenant_allowlist": ["kitchen_102"]},
        "rollout": {"strategy": "canary", "percent": 25.0},
        "fallback": "off",
        "metadata": {"owner": "tests"},
    }


def _decode_event(body: bytes) -> Dict[str, object]:
    prefix = b"data: "
    assert body.startswith(prefix)
    payload = body[len(prefix) :].strip()
    return json.loads(payload)


def _entry_model(payload: Dict[str, object]):
    from prep.platform.rcs.models import ConfigEntry

    return ConfigEntry(**payload)
