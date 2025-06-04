"""Prep Assist Protocol
=======================
API standard to connect with robotic kitchen tools.
"""

import json
import asyncio
import websockets

PROTOCOL_VERSION = "1.0"

async def send_command(uri: str, command: dict) -> dict:
    """Send a command to a robot via WebSocket."""
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps(command))
        response = await ws.recv()
        return json.loads(response)

async def reserve_station(uri: str, station: str) -> None:
    command = {"action": "reserve", "station": station}
    await send_command(uri, command)
