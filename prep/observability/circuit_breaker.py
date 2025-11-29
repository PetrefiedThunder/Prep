"""Circuit breaker pattern implementation for resilient external service calls.

This module provides:
- Circuit breaker state machine (CLOSED -> OPEN -> HALF_OPEN)
- Configurable failure thresholds and recovery times
- Async-compatible implementation
- Decorator and context manager interfaces
- Metrics integration for monitoring

The circuit breaker prevents cascading failures by:
1. Failing fast when a service is unhealthy
2. Allowing periodic recovery attempts
3. Returning to normal operation when health is restored
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

from prep.observability.logging_config import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Circuit tripped, requests fail fast
    HALF_OPEN = "half_open"  # Testing recovery, limited requests allowed


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(
        self,
        service_name: str,
        state: CircuitState,
        retry_after: float | None = None,
    ):
        self.service_name = service_name
        self.state = state
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker for '{service_name}' is {state.value}"
            + (f", retry after {retry_after:.1f}s" if retry_after else "")
        )


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    # Number of failures before opening circuit
    failure_threshold: int = 5

    # Time window for counting failures (seconds)
    failure_window: float = 60.0

    # Time to wait before trying recovery (seconds)
    recovery_timeout: float = 30.0

    # Number of successful calls to close circuit from half-open
    success_threshold: int = 3

    # Exceptions that should trigger the circuit (None = all exceptions)
    tracked_exceptions: tuple[type[Exception], ...] | None = None

    # Exceptions that should NOT trigger the circuit
    excluded_exceptions: tuple[type[Exception], ...] = ()

    # Time window for half-open state (seconds)
    half_open_timeout: float = 10.0

    # Maximum concurrent requests in half-open state
    half_open_max_calls: int = 1


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_transitions: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    current_state: CircuitState = CircuitState.CLOSED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "rejected_calls": self.rejected_calls,
            "state_transitions": self.state_transitions,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "current_state": self.current_state.value,
            "success_rate": (
                self.successful_calls / self.total_calls * 100
                if self.total_calls > 0
                else 0
            ),
        }


class CircuitBreaker:
    """Circuit breaker for protecting external service calls.

    Usage:
        # As a decorator
        breaker = CircuitBreaker("payment-service")

        @breaker
        async def call_payment_api():
            ...

        # As a context manager
        async with breaker:
            await call_external_service()

        # Manual execution
        result = await breaker.execute(call_payment_api, arg1, arg2)
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ):
        """Initialize circuit breaker.

        Args:
            name: Service name for logging and metrics
            config: Configuration options
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self._state = CircuitState.CLOSED
        self._failure_times: deque[float] = deque()
        self._success_count = 0
        self._half_open_calls = 0
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()

        self.stats = CircuitBreakerStats()

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self._state == CircuitState.HALF_OPEN

    def _should_track_exception(self, exc: Exception) -> bool:
        """Determine if exception should count toward failures."""
        # Check excluded exceptions first
        if isinstance(exc, self.config.excluded_exceptions):
            return False

        # If tracked_exceptions is specified, only track those
        if self.config.tracked_exceptions is not None:
            return isinstance(exc, self.config.tracked_exceptions)

        # Default: track all exceptions
        return True

    def _check_state_transition(self) -> None:
        """Check and perform state transitions based on current conditions."""
        current_time = time.time()

        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._opened_at is not None:
                elapsed = current_time - self._opened_at
                if elapsed >= self.config.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)

        elif self._state == CircuitState.CLOSED:
            # Clean up old failures outside the window
            window_start = current_time - self.config.failure_window
            while self._failure_times and self._failure_times[0] < window_start:
                self._failure_times.popleft()

            # Check if failure threshold exceeded
            if len(self._failure_times) >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self.stats.state_transitions += 1
        self.stats.current_state = new_state

        logger.warning(
            f"Circuit breaker '{self.name}' transitioned: {old_state.value} -> {new_state.value}",
            extra={
                "circuit_breaker": self.name,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "failure_count": len(self._failure_times),
            },
        )

        if new_state == CircuitState.OPEN:
            self._opened_at = time.time()
            self._half_open_calls = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_times.clear()
            self._success_count = 0

    def _record_success(self) -> None:
        """Record a successful call."""
        self.stats.successful_calls += 1
        self.stats.last_success_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)

    def _record_failure(self, exc: Exception) -> None:
        """Record a failed call."""
        if not self._should_track_exception(exc):
            return

        current_time = time.time()
        self._failure_times.append(current_time)
        self.stats.failed_calls += 1
        self.stats.last_failure_time = current_time

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open returns to open
            self._transition_to(CircuitState.OPEN)
        else:
            self._check_state_transition()

    def _can_execute(self) -> bool:
        """Check if a call can be executed."""
        self._check_state_transition()

        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            return False

        # Half-open: limit concurrent calls
        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.config.half_open_max_calls:
                return False
            self._half_open_calls += 1
            return True

        return False

    def _get_retry_after(self) -> float | None:
        """Calculate time until circuit might close."""
        if self._state != CircuitState.OPEN:
            return None

        if self._opened_at is None:
            return self.config.recovery_timeout

        elapsed = time.time() - self._opened_at
        remaining = self.config.recovery_timeout - elapsed
        return max(0, remaining)

    async def execute(
        self,
        func: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """Execute a function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function raises and circuit is not open
        """
        self.stats.total_calls += 1

        async with self._lock:
            can_execute = self._can_execute()

        if not can_execute:
            self.stats.rejected_calls += 1
            raise CircuitBreakerError(
                self.name,
                self._state,
                retry_after=self._get_retry_after(),
            )

        try:
            # Handle both sync and async functions
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            async with self._lock:
                self._record_success()

            return result

        except Exception as exc:
            async with self._lock:
                self._record_failure(exc)
            raise

    def __call__(
        self,
        func: Callable[P, T],
    ) -> Callable[P, T]:
        """Decorator interface for circuit breaker.

        Usage:
            @circuit_breaker
            async def my_function():
                ...
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await self.execute(func, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    async def __aenter__(self) -> CircuitBreaker:
        """Context manager entry."""
        self.stats.total_calls += 1

        async with self._lock:
            can_execute = self._can_execute()

        if not can_execute:
            self.stats.rejected_calls += 1
            raise CircuitBreakerError(
                self.name,
                self._state,
                retry_after=self._get_retry_after(),
            )

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        """Context manager exit."""
        async with self._lock:
            if exc_val is None:
                self._record_success()
            elif isinstance(exc_val, Exception):
                self._record_failure(exc_val)

        return False  # Don't suppress exceptions

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._failure_times.clear()
        self._success_count = 0
        self._half_open_calls = 0
        self._opened_at = None
        self.stats = CircuitBreakerStats()

        logger.info(
            f"Circuit breaker '{self.name}' reset to CLOSED state",
            extra={"circuit_breaker": self.name},
        )


# Registry of circuit breakers for monitoring
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    config: CircuitBreakerConfig | None = None,
) -> CircuitBreaker:
    """Get or create a circuit breaker by name.

    This allows sharing circuit breakers across multiple call sites.

    Args:
        name: Service name
        config: Configuration (only used if creating new breaker)

    Returns:
        Circuit breaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def get_all_circuit_breaker_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all circuit breakers.

    Returns:
        Dictionary mapping service names to their stats
    """
    return {name: cb.stats.to_dict() for name, cb in _circuit_breakers.items()}


def circuit_breaker(
    name: str,
    *,
    failure_threshold: int = 5,
    failure_window: float = 60.0,
    recovery_timeout: float = 30.0,
    success_threshold: int = 3,
    tracked_exceptions: tuple[type[Exception], ...] | None = None,
    excluded_exceptions: tuple[type[Exception], ...] = (),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator factory for circuit breaker.

    Usage:
        @circuit_breaker("payment-service", failure_threshold=3)
        async def call_payment_api():
            ...

    Args:
        name: Service name for logging and metrics
        failure_threshold: Failures before opening circuit
        failure_window: Time window for counting failures
        recovery_timeout: Time before recovery attempt
        success_threshold: Successes to close circuit
        tracked_exceptions: Exceptions to track (None = all)
        excluded_exceptions: Exceptions to ignore

    Returns:
        Decorator function
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        failure_window=failure_window,
        recovery_timeout=recovery_timeout,
        success_threshold=success_threshold,
        tracked_exceptions=tracked_exceptions,
        excluded_exceptions=excluded_exceptions,
    )

    breaker = get_circuit_breaker(name, config)

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        return breaker(func)

    return decorator


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerError",
    "CircuitBreakerStats",
    "CircuitState",
    "circuit_breaker",
    "get_all_circuit_breaker_stats",
    "get_circuit_breaker",
]
