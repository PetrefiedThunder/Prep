import logging
import time
from typing import Callable, Optional


class SafetyDaemon:
    def __init__(self, check_interval: int = 60, logger: Optional[logging.Logger] = None):
        self.check_interval = check_interval
        self.logger = logger or logging.getLogger(__name__)

    def monitor(
        self,
        stop_flag: Optional[Callable[[], bool]] = None,
        iterations: Optional[int] = None,
    ) -> int:
        """Monitor safety conditions.

        Args:
            stop_flag: Callable returning True to stop the loop.
            iterations: Maximum number of iterations to run.

        Returns:
            The number of safety checks performed.
        """

        count = 0
        while True:
            if stop_flag and stop_flag():
                break
            if iterations is not None and count >= iterations:
                break
            # Placeholder for sensor checks
            self.logger.info("Performing safety check...")
            time.sleep(self.check_interval)
            count += 1
        return count
import asyncio
import inspect
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Optional


class SafetyDaemon:
    def __init__(
        self,
        check_interval: int = 60,
        logger: Optional[logging.Logger] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        event_handler: Optional[Callable[[str, str], Awaitable[None] | None]] = None,
    ):
        self.check_interval = check_interval
        self.logger = logger or logging.getLogger(__name__)
        self._stop = asyncio.Event()
        self.sleep_fn = sleep_fn
        self._event_handler = event_handler

    def stop(self) -> None:
        self._stop.set()

    def set_event_handler(
        self, handler: Optional[Callable[[str, str], Awaitable[None] | None]]
    ) -> None:
        """Register a callback for safety events.

        The handler may be synchronous or asynchronous. When asynchronous,
        the coroutine is awaited before continuing with the monitor loop.
        """

        self._event_handler = handler

    async def monitor(self, iterations: Optional[int] = None) -> None:
        count = 0
        while not self._stop.is_set():
            # Placeholder for sensor checks
            message = "Performing safety check..."
            self.logger.info(message)
            if self._event_handler is not None:
                try:
                    result = self._event_handler("safety_check", message)
                    if inspect.isawaitable(result):
                        await result
                except Exception:  # pragma: no cover - defensive logging
                    self.logger.exception("Safety event handler failed")

            # Run the sleep function in a thread so the event loop is not blocked
            sleep_task = asyncio.create_task(
                asyncio.to_thread(self.sleep_fn, self.check_interval)
            )
            stop_task = asyncio.create_task(self._stop.wait())

            done, pending = await asyncio.wait(
                {sleep_task, stop_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            if stop_task in done:
                break
            count += 1
            if iterations is not None and count >= iterations:
                break
