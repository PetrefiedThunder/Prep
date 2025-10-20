import asyncio
import logging
from typing import List

from modules.kitchen_safety_daemon.daemon import SafetyDaemon


def test_monitor_iterations(caplog):
    daemon = SafetyDaemon(check_interval=0)
    with caplog.at_level(logging.INFO):
        count = daemon.monitor(iterations=2, sleep_fn=lambda _: None)
    assert count == 2
    assert caplog.text.count("Performing safety check...") >= 2


def test_monitor_async_iterations(caplog):
    daemon = SafetyDaemon(check_interval=0, sleep_fn=lambda _: None)

    async def run() -> int:
        with caplog.at_level(logging.INFO):
            return await daemon.monitor_async(iterations=2)

    count = asyncio.run(run())
    assert count == 2
    assert caplog.text.count("Performing safety check...") >= 2


def test_monitor_stop_flag(caplog):
    daemon = SafetyDaemon(check_interval=0)
    stop_iter = iter([False, True])

    def stop_flag():
        return next(stop_iter)

    with caplog.at_level(logging.INFO):
        count = daemon.monitor(stop_flag=stop_flag, sleep_fn=lambda _: None)
    assert count == 1
    assert caplog.text.count("Performing safety check...") == 1


def test_async_stop(caplog):
    daemon = SafetyDaemon(check_interval=0.01, sleep_fn=lambda _: asyncio.sleep(0))

    async def run() -> None:
        with caplog.at_level(logging.INFO):
            task = asyncio.create_task(daemon.monitor_async())
            await asyncio.sleep(0)
            daemon.stop()
            await task

    asyncio.run(run())
    assert "Performing safety check..." in caplog.text


def test_async_event_handler_invoked():
    events: List[str] = []

    async def handler(event: str, message: str) -> None:
        events.append(f"{event}:{message}")

    async def run() -> None:
        daemon = SafetyDaemon(
            check_interval=0,
            sleep_fn=lambda _: None,
            event_handler=handler,
        )
        await daemon.monitor_async(iterations=1)

    asyncio.run(run())
    assert events == ["safety_check:Performing safety check..."]


def test_sync_event_handler_invoked():
    events: List[str] = []

    def handler(event: str, message: str) -> None:
        events.append(f"{event}:{message}")

    async def run() -> None:
        daemon = SafetyDaemon(
            check_interval=0,
            sleep_fn=lambda _: None,
            event_handler=handler,
        )
        await daemon.monitor_async(iterations=1)

    asyncio.run(run())
    assert events == ["safety_check:Performing safety check..."]
