from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Optional


class SafetyDaemon:
    """Run synchronous or asynchronous kitchen safety checks."""

    def __init__(
        self,
        check_interval: float = 60,
        logger: Optional[logging.Logger] = None,
        *,
        sleep_fn: Callable[[float], object] = time.sleep,
        event_handler: Optional[Callable[[str, str], Awaitable[None] | None]] = None,
    ) -> None:
        self.check_interval = check_interval
        self.logger = logger or logging.getLogger(__name__)
        self._async_sleep = sleep_fn
        self._event_handler = event_handler
        self._stop_event = asyncio.Event()

    # ------------------------------------------------------------------
    # Synchronous monitoring
    # ------------------------------------------------------------------
    def monitor(
        self,
        *,
        stop_flag: Optional[Callable[[], bool]] = None,
        iterations: Optional[int] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> int:
        count = 0
        while True:
            if stop_flag and stop_flag():
                break
            if iterations is not None and count >= iterations:
                break

            message = "Performing safety check..."
            self.logger.info(message)
            sleep_fn(self.check_interval)
            count += 1

        return count

    # ------------------------------------------------------------------
    # Asynchronous monitoring
    # ------------------------------------------------------------------
    def stop(self) -> None:
        self._stop_event.set()

    def set_event_handler(
        self, handler: Optional[Callable[[str, str], Awaitable[None] | None]]
    ) -> None:
        self._event_handler = handler

    async def monitor_async(self, iterations: Optional[int] = None) -> int:
        count = 0
        self._stop_event.clear()

        while not self._stop_event.is_set():
            message = "Performing safety check..."
            self.logger.info(message)

            if self._event_handler is not None:
                try:
                    result = self._event_handler("safety_check", message)
                    if inspect.isawaitable(result):
                        await result
                except Exception:  # pragma: no cover - defensive logging
                    self.logger.exception("Safety event handler failed")

            count += 1
            if iterations is not None and count >= iterations:
                break

            await self._sleep_once()

        return count

    async def _sleep_once(self) -> None:
        sleep_callable = self._async_sleep

        if inspect.iscoroutinefunction(sleep_callable):
            await sleep_callable(self.check_interval)
            return

        call_attr = getattr(sleep_callable, "__call__", None)
        if call_attr is not None and inspect.iscoroutinefunction(call_attr):
            await sleep_callable(self.check_interval)  # type: ignore[misc]
            return

        result = await asyncio.to_thread(
            time.sleep if sleep_callable is time.sleep else sleep_callable,
            self.check_interval,
        )
        if inspect.isawaitable(result):
            await result
