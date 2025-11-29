"""Retry mechanism with exponential backoff for resilient external service calls.

This module provides:
- Configurable retry policies with exponential backoff
- Jitter to prevent thundering herd
- Retry budgets to limit total retry attempts
- Integration with circuit breaker pattern
- Async-compatible decorators and context managers
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

from prep.observability.logging_config import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    # Maximum number of retry attempts (0 = no retries)
    max_retries: int = 3

    # Initial delay between retries (seconds)
    initial_delay: float = 1.0

    # Maximum delay between retries (seconds)
    max_delay: float = 60.0

    # Multiplier for exponential backoff
    backoff_multiplier: float = 2.0

    # Jitter factor (0.0 to 1.0) - randomizes delay to prevent thundering herd
    jitter: float = 0.1

    # Exceptions that should trigger a retry (None = all exceptions)
    retryable_exceptions: tuple[type[Exception], ...] | None = None

    # Exceptions that should NOT be retried
    non_retryable_exceptions: tuple[type[Exception], ...] = ()

    # HTTP status codes that should trigger a retry (for HTTP clients)
    retryable_status_codes: tuple[int, ...] = (408, 429, 500, 502, 503, 504)

    # Whether to retry on timeout
    retry_on_timeout: bool = True


@dataclass
class RetryStats:
    """Statistics for retry operations."""

    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_retries: int = 0
    last_error: str | None = None
    last_attempt_time: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "total_retries": self.total_retries,
            "success_rate": (
                self.successful_attempts / self.total_attempts * 100
                if self.total_attempts > 0
                else 0
            ),
            "last_error": self.last_error,
            "last_attempt_time": self.last_attempt_time,
        }


class RetryBudget:
    """Limits total retry attempts across all operations within a time window.

    Prevents retry storms by enforcing a budget on retries.
    """

    def __init__(
        self,
        *,
        max_retries_per_window: int = 100,
        window_seconds: float = 60.0,
        min_retry_ratio: float = 0.1,
    ):
        """Initialize retry budget.

        Args:
            max_retries_per_window: Maximum retries allowed in the window
            window_seconds: Time window for budget reset
            min_retry_ratio: Minimum ratio of retries to total requests
        """
        self.max_retries_per_window = max_retries_per_window
        self.window_seconds = window_seconds
        self.min_retry_ratio = min_retry_ratio

        self._window_start = time.time()
        self._requests_in_window = 0
        self._retries_in_window = 0
        self._lock = asyncio.Lock()

    async def can_retry(self) -> bool:
        """Check if a retry is allowed within the budget."""
        async with self._lock:
            current_time = time.time()

            # Reset window if expired
            if current_time - self._window_start >= self.window_seconds:
                self._window_start = current_time
                self._requests_in_window = 0
                self._retries_in_window = 0

            # Check absolute limit
            if self._retries_in_window >= self.max_retries_per_window:
                return False

            # Check ratio limit (only after some requests)
            if self._requests_in_window > 10:
                current_ratio = self._retries_in_window / self._requests_in_window
                if current_ratio >= self.min_retry_ratio:
                    return False

            return True

    async def record_request(self) -> None:
        """Record a new request."""
        async with self._lock:
            self._requests_in_window += 1

    async def record_retry(self) -> None:
        """Record a retry attempt."""
        async with self._lock:
            self._retries_in_window += 1


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(
        self,
        message: str,
        attempts: int,
        last_exception: Exception | None = None,
    ):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(message)


def _calculate_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """Calculate delay with exponential backoff and jitter."""
    # Exponential backoff
    delay = config.initial_delay * (config.backoff_multiplier**attempt)

    # Cap at maximum delay
    delay = min(delay, config.max_delay)

    # Add jitter
    if config.jitter > 0:
        jitter_range = delay * config.jitter
        delay = delay + random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


def _should_retry(
    exc: Exception,
    config: RetryConfig,
) -> bool:
    """Determine if an exception should trigger a retry."""
    # Check non-retryable exceptions first
    if isinstance(exc, config.non_retryable_exceptions):
        return False

    # Check timeout
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return config.retry_on_timeout

    # Check retryable exceptions
    if config.retryable_exceptions is not None:
        return isinstance(exc, config.retryable_exceptions)

    # Default: retry all exceptions not explicitly excluded
    return True


class Retry:
    """Retry handler with exponential backoff.

    Usage:
        # As a decorator
        retry = Retry(max_retries=3)

        @retry
        async def call_external_api():
            ...

        # As a context manager
        async with Retry(max_retries=3) as retry:
            result = await retry.execute(call_api)

        # Manual execution
        retry = Retry()
        result = await retry.execute(call_api, arg1, arg2)
    """

    def __init__(
        self,
        config: RetryConfig | None = None,
        *,
        max_retries: int | None = None,
        initial_delay: float | None = None,
        max_delay: float | None = None,
        budget: RetryBudget | None = None,
    ):
        """Initialize retry handler.

        Args:
            config: Full retry configuration
            max_retries: Override max retries (convenience parameter)
            initial_delay: Override initial delay (convenience parameter)
            max_delay: Override max delay (convenience parameter)
            budget: Optional retry budget for rate limiting
        """
        self.config = config or RetryConfig()

        # Apply convenience overrides
        if max_retries is not None:
            self.config.max_retries = max_retries
        if initial_delay is not None:
            self.config.initial_delay = initial_delay
        if max_delay is not None:
            self.config.max_delay = max_delay

        self.budget = budget
        self.stats = RetryStats()

    async def execute(
        self,
        func: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """Execute a function with retry logic.

        Args:
            func: Function to execute (sync or async)
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            RetryError: If all retry attempts fail
        """
        self.stats.total_attempts += 1

        if self.budget:
            await self.budget.record_request()

        last_exception: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Success
                self.stats.successful_attempts += 1
                self.stats.last_attempt_time = time.time()

                if attempt > 0:
                    logger.info(
                        f"Operation succeeded after {attempt} retries",
                        extra={
                            "attempts": attempt + 1,
                            "function": func.__name__,
                        },
                    )

                return result

            except Exception as exc:
                last_exception = exc
                self.stats.last_error = str(exc)
                self.stats.last_attempt_time = time.time()

                # Check if we should retry
                if not _should_retry(exc, self.config):
                    logger.warning(
                        f"Non-retryable exception: {type(exc).__name__}",
                        extra={
                            "function": func.__name__,
                            "error": str(exc),
                        },
                    )
                    raise

                # Check if we have retries left
                if attempt >= self.config.max_retries:
                    break

                # Check retry budget
                if self.budget and not await self.budget.can_retry():
                    logger.warning(
                        "Retry budget exhausted, not retrying",
                        extra={"function": func.__name__},
                    )
                    break

                # Calculate delay
                delay = _calculate_delay(attempt, self.config)

                logger.warning(
                    f"Retry {attempt + 1}/{self.config.max_retries} after {delay:.2f}s: {type(exc).__name__}",
                    extra={
                        "function": func.__name__,
                        "attempt": attempt + 1,
                        "max_retries": self.config.max_retries,
                        "delay": delay,
                        "error": str(exc),
                    },
                )

                # Record retry
                self.stats.total_retries += 1
                if self.budget:
                    await self.budget.record_retry()

                # Wait before retry
                await asyncio.sleep(delay)

        # All retries exhausted
        self.stats.failed_attempts += 1

        error_msg = (
            f"All {self.config.max_retries + 1} attempts failed for {func.__name__}"
        )
        logger.error(
            error_msg,
            extra={
                "function": func.__name__,
                "total_attempts": self.config.max_retries + 1,
                "last_error": str(last_exception),
            },
        )

        raise RetryError(
            error_msg,
            attempts=self.config.max_retries + 1,
            last_exception=last_exception,
        )

    def __call__(
        self,
        func: Callable[P, T],
    ) -> Callable[P, T]:
        """Decorator interface for retry."""

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await self.execute(func, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    async def __aenter__(self) -> Retry:
        """Context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        """Context manager exit."""
        return False  # Don't suppress exceptions


def retry(
    *,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    jitter: float = 0.1,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
    non_retryable_exceptions: tuple[type[Exception], ...] = (),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator factory for retry with exponential backoff.

    Usage:
        @retry(max_retries=5, initial_delay=0.5)
        async def call_external_service():
            ...

    Args:
        max_retries: Maximum retry attempts
        initial_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        backoff_multiplier: Multiplier for exponential backoff
        jitter: Jitter factor (0.0 to 1.0)
        retryable_exceptions: Exceptions to retry (None = all)
        non_retryable_exceptions: Exceptions to not retry

    Returns:
        Decorator function
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_multiplier=backoff_multiplier,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
        non_retryable_exceptions=non_retryable_exceptions,
    )

    retry_handler = Retry(config)

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        return retry_handler(func)

    return decorator


# Convenience function for one-off retries
async def retry_async(
    func: Callable[P, T],
    *args: P.args,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    **kwargs: P.kwargs,
) -> T:
    """Execute a function with retry logic (one-off usage).

    Usage:
        result = await retry_async(call_api, arg1, max_retries=5)

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        max_retries: Maximum retry attempts
        initial_delay: Initial delay between retries
        **kwargs: Keyword arguments for the function

    Returns:
        Function result
    """
    retry_handler = Retry(max_retries=max_retries, initial_delay=initial_delay)
    return await retry_handler.execute(func, *args, **kwargs)


__all__ = [
    "Retry",
    "RetryBudget",
    "RetryConfig",
    "RetryError",
    "RetryStats",
    "retry",
    "retry_async",
]
