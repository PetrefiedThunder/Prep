import asyncio
import logging
import time
from typing import Awaitable, Callable, Optional


async def _default_sleep(delay: float) -> None:
    """Default sleep function using ``time.sleep`` in a thread."""
    await asyncio.to_thread(time.sleep, delay)


class SafetyDaemon:
    def __init__(
        self,
        check_interval: int = 60,
        logger: Optional[logging.Logger] = None,
        sleep_fn: Callable[[float], Awaitable[None]] = _default_sleep,
    ):
        self.check_interval = check_interval
        self.logger = logger or logging.getLogger(__name__)
        self._stop = False
        self.sleep_fn = sleep_fn

    def stop(self) -> None:
        self._stop = True

    async def monitor(self, iterations: Optional[int] = None) -> None:
        count = 0
        while not self._stop:
            # Placeholder for sensor checks
            self.logger.info("Performing safety check...")
            await self.sleep_fn(self.check_interval)
            count += 1
            if iterations is not None and count >= iterations:
                break
