import logging
import asyncio
import logging
from typing import List

from modules.kitchen_safety_daemon.daemon import SafetyDaemon


def test_monitor_iterations(caplog):
    daemon = SafetyDaemon(check_interval=0)
    with caplog.at_level(logging.INFO):
        count = daemon.monitor(iterations=2)
    assert count == 2
    def fast_sleep(_: float) -> None:
        pass

    async def run() -> None:
        logger = logging.getLogger("test.daemon.iter")
        daemon = SafetyDaemon(check_interval=0, logger=logger, sleep_fn=fast_sleep)
        with caplog.at_level(logging.INFO, logger="test.daemon.iter"):
            await daemon.monitor(iterations=2)

    asyncio.run(run())
    assert caplog.text.count("Performing safety check...") == 2


def test_monitor_stop_flag(caplog):
    daemon = SafetyDaemon(check_interval=0)
    stop_iter = iter([False, True])

    def stop_flag():
        return next(stop_iter)

    with caplog.at_level(logging.INFO):
        count = daemon.monitor(stop_flag=stop_flag)
    assert count == 1
    assert caplog.text.count("Performing safety check...") == 1
    def fast_sleep(_: float) -> None:
        pass

    async def run() -> None:
        logger = logging.getLogger("test.daemon.stop")
        daemon = SafetyDaemon(check_interval=0.01, logger=logger, sleep_fn=fast_sleep)
        with caplog.at_level(logging.INFO, logger="test.daemon.stop"):
            task = asyncio.create_task(daemon.monitor())
            await asyncio.sleep(0)  # allow the monitor to start
            daemon.stop()
            await task

    asyncio.run(run())
    assert "Performing safety check..." in caplog.text


def test_monitor_allows_async_sleep():
    async def run() -> None:
        async_called = asyncio.Event()

        async def async_sleep(delay: float) -> None:
            async_called.set()
            await asyncio.sleep(0)

        daemon = SafetyDaemon(check_interval=0.01, sleep_fn=async_sleep)
        monitor_task = asyncio.create_task(daemon.monitor())

        await asyncio.wait_for(async_called.wait(), timeout=1)
        daemon.stop()
        await monitor_task

    asyncio.run(run())


def test_monitor_allows_async_callable_object():
    async def run() -> None:
        event = asyncio.Event()

        class AsyncSleeper:
            async def __call__(self, delay: float) -> None:  # pragma: no cover - exercised via daemon
                event.set()
                await asyncio.sleep(0)

        daemon = SafetyDaemon(check_interval=0.01, sleep_fn=AsyncSleeper())
        monitor_task = asyncio.create_task(daemon.monitor())

        await asyncio.wait_for(event.wait(), timeout=1)
        daemon.stop()
        await monitor_task

    asyncio.run(run())


def test_monitor_awaits_coroutine_returned_from_sync_callable():
    async def run() -> None:
        event = asyncio.Event()

        def returns_coroutine(delay: float):
            async def sleeper() -> None:
                event.set()
                await asyncio.sleep(0)

            return sleeper()

        daemon = SafetyDaemon(check_interval=0.01, sleep_fn=returns_coroutine)
        monitor_task = asyncio.create_task(daemon.monitor())

        await asyncio.wait_for(event.wait(), timeout=1)
        daemon.stop()
        await monitor_task

    asyncio.run(run())
def test_event_handler_invoked():
    def fast_sleep(_: float) -> None:
        pass

    events: List[tuple[str, str]] = []

    def handler(event: str, message: str) -> None:
        events.append((event, message))

    async def run() -> None:
        daemon = SafetyDaemon(
            check_interval=0,
            sleep_fn=fast_sleep,
            event_handler=handler,
        )
        await daemon.monitor(iterations=1)

    asyncio.run(run())
    assert events == [("safety_check", "Performing safety check...")]


def test_async_event_handler_invoked():
    def fast_sleep(_: float) -> None:
        pass

    events: List[str] = []

    async def handler(event: str, message: str) -> None:
        events.append(f"{event}:{message}")

    async def run() -> None:
        daemon = SafetyDaemon(
            check_interval=0,
            sleep_fn=fast_sleep,
            event_handler=handler,
        )
        await daemon.monitor(iterations=1)

    asyncio.run(run())
    assert events == ["safety_check:Performing safety check..."]

