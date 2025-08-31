import asyncio
import logging

from modules.kitchen_safety_daemon.daemon import SafetyDaemon


def test_monitor_iterations(caplog):
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

