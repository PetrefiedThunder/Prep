"""Safety monitoring daemon with injectable sleep and event handler support."""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Optional


SleepFn = Callable[[float], Awaitable[None] | None]
EventHandler = Callable[[str, str], Awaitable[None] | None]


class SafetyDaemon:
    def __init__(
        self,
        check_interval: int = 60,
        logger: Optional[logging.Logger] = None,
        sleep_fn: SleepFn = time.sleep,
        event_handler: Optional[EventHandler] = None,
    ):
        self.check_interval = check_interval
        self.logger = logger or logging.getLogger(__name__)
        self._stop = asyncio.Event()
        self.sleep_fn = sleep_fn
        self._event_handler = event_handler

    def stop(self) -> None:
        self._stop.set()

    def set_event_handler(self, handler: Optional[EventHandler]) -> None:
        """Register a callback for safety events."""

        self._event_handler = handler

    async def monitor(self, iterations: Optional[int] = None) -> None:
        count = 0
        while not self._stop.is_set():
            message = "Performing safety check..."
            self.logger.info(message)

            if self._event_handler is not None:
                try:
                    result = self._event_handler("safety_check", message)
                    if inspect.isawaitable(result):
                        await result
                except Exception:  # pragma: no cover - defensive logging
                    self.logger.exception("Safety event handler failed")

            sleep_task = asyncio.create_task(self._sleep_once())
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

    async def _sleep_once(self) -> None:
        sleep_callable = self.sleep_fn

        if inspect.iscoroutinefunction(sleep_callable):
            await sleep_callable(self.check_interval)
            return

        call_attr = getattr(sleep_callable, "__call__", None)
        if call_attr is not None and inspect.iscoroutinefunction(call_attr):
            await sleep_callable(self.check_interval)
            return

        type_call_attr = getattr(type(sleep_callable), "__call__", None)
        if type_call_attr is not None and inspect.iscoroutinefunction(type_call_attr):
            await sleep_callable(self.check_interval)
            return

        result = await asyncio.to_thread(sleep_callable, self.check_interval)
        if inspect.isawaitable(result):
            await result
