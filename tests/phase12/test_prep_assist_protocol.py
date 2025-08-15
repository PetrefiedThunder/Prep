import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from phase12 import prep_assist_protocol


def test_send_command_connection_failure():
    async def run():
        with patch(
            "phase12.prep_assist_protocol.websockets.connect", side_effect=OSError("fail")
        ):
            await prep_assist_protocol.send_command("ws://robot", {"a": 1})

    with pytest.raises(ConnectionError):
        asyncio.run(run())


def test_send_command_send_failure():
    mock_ws = AsyncMock()
    mock_ws.send.side_effect = Exception("send")
    connect_cm = AsyncMock()
    connect_cm.__aenter__.return_value = mock_ws
    connect_cm.__aexit__.return_value = False

    async def run():
        with patch("phase12.prep_assist_protocol.websockets.connect", return_value=connect_cm):
            await prep_assist_protocol.send_command("ws://robot", {"a": 1})

    with pytest.raises(RuntimeError):
        asyncio.run(run())


def test_send_command_receive_failure():
    mock_ws = AsyncMock()
    mock_ws.send.return_value = None
    mock_ws.recv.side_effect = Exception("recv")
    connect_cm = AsyncMock()
    connect_cm.__aenter__.return_value = mock_ws
    connect_cm.__aexit__.return_value = False

    async def run():
        with patch("phase12.prep_assist_protocol.websockets.connect", return_value=connect_cm):
            await prep_assist_protocol.send_command("ws://robot", {"a": 1})

    with pytest.raises(RuntimeError):
        asyncio.run(run())
