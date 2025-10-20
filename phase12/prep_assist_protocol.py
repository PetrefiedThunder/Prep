"""Prep Assist Protocol
=======================
API standard to connect with robotic kitchen tools.
"""

import json
import logging
from typing import Any, Dict, cast
try:
    import websockets  # type: ignore
except ImportError:  # pragma: no cover
    class _WebsocketStub:
        connect = None

    websockets = _WebsocketStub()

PROTOCOL_VERSION = "1.0"

async def send_command(uri: str, command: Dict[str, Any]) -> Dict[str, Any]:
    """Send a command to a robot via WebSocket."""
async def send_command(
    uri: str,
    command: dict,
    send_timeout: float | None = 5.0,
    recv_timeout: float | None = 5.0,
) -> dict:
    """Send a command to a robot via WebSocket.

    Parameters
    ----------
    uri:
        WebSocket URI of the robot.
    command:
        Command payload to send.
    send_timeout:
        Maximum time in seconds to wait for the send to complete.
    recv_timeout:
        Maximum time in seconds to wait for the response.
    """
    if getattr(websockets, "connect", None) is None:  # pragma: no cover - dependency missing
        raise ImportError("websockets library is required")
    try:
        async with websockets.connect(uri) as ws:
            try:
                await asyncio.wait_for(
                    ws.send(json.dumps(command)), timeout=send_timeout
                )
            except Exception as exc:
                logging.error("Failed to send command to %s: %s", uri, exc)
                raise RuntimeError("WebSocket send failed") from exc
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=recv_timeout)
            except Exception as exc:
                logging.error("Failed to receive response from %s: %s", uri, exc)
                raise RuntimeError("WebSocket receive failed") from exc
    except OSError as exc:
        logging.error("Failed to connect to %s: %s", uri, exc)
        raise ConnectionError("WebSocket connection failed") from exc
    return cast(Dict[str, Any], json.loads(response))

async def reserve_station(uri: str, station: str) -> None:
    command = {"action": "reserve", "station": station}
    await send_command(uri, command)
