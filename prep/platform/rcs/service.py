"""Minimal ASGI application exposing the Realtime Configuration Service."""

from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional
from urllib.parse import parse_qs

from .models import ChangeType, ConfigChange, ConfigEntry, ConfigRecord
from .storage import ConfigStore

JSON = Dict[str, Any]
Scope = Dict[str, Any]
ReceiveCallable = Callable[[], Awaitable[Dict[str, Any]]]
SendCallable = Callable[[Dict[str, Any]], Awaitable[None]]


class HTTPError(Exception):
    """Exception raised for HTTP errors."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class RCSApp:
    """Lightweight ASGI application for serving configuration data."""

    store: ConfigStore

    async def __call__(self, scope: Scope, receive: ReceiveCallable, send: SendCallable) -> None:
        if scope["type"] != "http":
            raise HTTPError(500, "Unsupported scope type")

        method = scope["method"].upper()
        path = scope["path"]
        query = parse_qs(scope.get("query_string", b"").decode("utf-8"))

        try:
            if path == "/healthz" and method == "GET":
                await self._send_json(send, {"status": "ok"})
            elif path == "/configs" and method == "GET":
                await self._handle_list(query, send)
            elif path.startswith("/configs/") and path != "/configs/stream":
                key = path[len("/configs/") :]
                if not key:
                    raise HTTPError(400, "Key must be provided")
                if method == "GET":
                    await self._handle_get(key, send)
                elif method == "PUT":
                    body = await self._receive_json(receive)
                    await self._handle_upsert(key, body, send)
                elif method == "DELETE":
                    await self._handle_delete(key, send)
                else:
                    raise HTTPError(405, "Method not allowed")
            elif path == "/configs/stream" and method == "GET":
                await self._handle_stream(query, receive, send)
            else:
                raise HTTPError(404, "Not found")
        except HTTPError as exc:
            await self._send_json(send, {"detail": exc.detail}, status_code=exc.status_code)

    async def _handle_list(self, query: Dict[str, list[str]], send: SendCallable) -> None:
        prefix = query.get("prefix", [None])[0]
        records = await self.store.list(prefix=prefix)
        payload = [record.model_dump() for record in records]
        await self._send_json(send, payload)

    async def _handle_get(self, key: str, send: SendCallable) -> None:
        record = await self.store.get(key)
        if record is None:
            raise HTTPError(404, "Config entry not found")
        await self._send_json(send, record.model_dump())

    async def _handle_upsert(self, key: str, body: JSON, send: SendCallable) -> None:
        if body.get("key") != key:
            raise HTTPError(400, "Key mismatch between path and payload")
        entry = ConfigEntry(**body)
        record = await self.store.upsert(entry)
        await self._send_json(send, record.model_dump())

    async def _handle_delete(self, key: str, send: SendCallable) -> None:
        record = await self.store.delete(key)
        if record is None:
            raise HTTPError(404, "Config entry not found")
        await self._send_json(send, None, status_code=204)

    async def _handle_stream(
        self, query: Dict[str, list[str]], receive: ReceiveCallable, send: SendCallable
    ) -> None:
        prefix = query.get("prefix", [None])[0]

        await _drain_request(receive)

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"text/event-stream"),
                    (b"cache-control", b"no-cache"),
                    (b"connection", b"keep-alive"),
                ],
            }
        )

        snapshot = await self.store.list(prefix=prefix)
        snapshot_payload = {
            "type": "snapshot",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "configs": [record.model_dump() for record in snapshot],
        }
        await send(
            {
                "type": "http.response.body",
                "body": _encode_sse(snapshot_payload),
                "more_body": True,
            }
        )

        disconnect_event = asyncio.Event()

        async def watch_disconnect() -> None:
            while True:
                message = await receive()
                if message.get("type") == "http.disconnect":
                    disconnect_event.set()
                    break

        watcher = asyncio.create_task(watch_disconnect())

        try:
            async with self.store.subscribe(prefix=prefix) as queue:
                disconnect_waiter = asyncio.create_task(disconnect_event.wait())
                try:
                    while True:
                        queue_waiter = asyncio.create_task(queue.get())
                        done, _ = await asyncio.wait(
                            {queue_waiter, disconnect_waiter},
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        if disconnect_waiter in done:
                            queue_waiter.cancel()
                            with contextlib.suppress(asyncio.CancelledError):
                                await queue_waiter
                            break
                        change = queue_waiter.result()
                        payload = _change_to_payload(change)
                        await send(
                            {
                                "type": "http.response.body",
                                "body": _encode_sse(payload),
                                "more_body": True,
                            }
                        )
                finally:
                    disconnect_waiter.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await disconnect_waiter
        finally:
            watcher.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watcher

        await send({"type": "http.response.body", "body": b""})

    async def _receive_json(self, receive: ReceiveCallable) -> JSON:
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                raise HTTPError(400, "Client disconnected")
            if message["type"] != "http.request":
                continue
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        if not body:
            raise HTTPError(400, "Request body is required")
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPError(400, "Invalid JSON payload") from exc

    async def _send_json(self, send: SendCallable, payload: Any, status_code: int = 200) -> None:
        headers = [(b"content-type", b"application/json")]
        await send({"type": "http.response.start", "status": status_code, "headers": headers})
        if payload is None:
            body = b""
        else:
            body = json.dumps(payload, default=_json_default).encode("utf-8")
        await send({"type": "http.response.body", "body": body})


def _encode_sse(payload: Dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, default=_json_default)}\n\n".encode("utf-8")


def _change_to_payload(change: ConfigChange) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "type": change.type.value,
        "key": change.key,
        "version": change.version,
        "emitted_at": change.emitted_at.isoformat(),
    }
    if change.type == ChangeType.UPSERT and change.record is not None:
        base["config"] = change.record.model_dump()
    return base


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


async def _drain_request(receive: ReceiveCallable) -> None:
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            raise HTTPError(400, "Client disconnected")
        if message["type"] != "http.request":
            continue
        if not message.get("more_body", False):
            break


def create_app(store: Optional[ConfigStore] = None) -> RCSApp:
    return RCSApp(store=store or ConfigStore())


app = create_app()
