"""Graceful shutdown handling for production deployments.

This module provides:
- Signal handlers for SIGTERM and SIGINT
- Connection draining before shutdown
- Configurable shutdown timeout
- Cleanup hooks for resources
- Integration with FastAPI lifespan
"""

from __future__ import annotations

import asyncio
import signal
import sys
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any

from prep.observability.logging_config import get_logger

logger = get_logger(__name__)


class GracefulShutdown:
    """Manages graceful shutdown for the application.

    Usage:
        shutdown_manager = GracefulShutdown()
        shutdown_manager.register_cleanup(cleanup_database)
        shutdown_manager.register_cleanup(cleanup_redis)
        shutdown_manager.install_signal_handlers()

    With FastAPI lifespan:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            shutdown_manager = GracefulShutdown()
            shutdown_manager.install_signal_handlers()
            yield
            await shutdown_manager.shutdown()
    """

    def __init__(
        self,
        *,
        shutdown_timeout: float = 30.0,
        drain_timeout: float = 10.0,
    ):
        """Initialize shutdown manager.

        Args:
            shutdown_timeout: Maximum time to wait for cleanup (seconds)
            drain_timeout: Time to wait for in-flight requests to complete
        """
        self.shutdown_timeout = shutdown_timeout
        self.drain_timeout = drain_timeout
        self._shutdown_event = asyncio.Event()
        self._cleanup_hooks: list[Callable[[], Coroutine[Any, Any, None]]] = []
        self._is_shutting_down = False
        self._active_connections: int = 0
        self._lock = asyncio.Lock()

    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown has been initiated."""
        return self._is_shutting_down

    def register_cleanup(
        self,
        cleanup_func: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        """Register an async cleanup function to run during shutdown.

        Cleanup functions are called in reverse order of registration
        (LIFO - Last In, First Out).

        Args:
            cleanup_func: Async function that performs cleanup
        """
        self._cleanup_hooks.append(cleanup_func)
        logger.debug(f"Registered cleanup hook: {cleanup_func.__name__}")

    def install_signal_handlers(self) -> None:
        """Install signal handlers for graceful shutdown.

        Handles:
        - SIGTERM: Standard termination signal (Docker, Kubernetes)
        - SIGINT: Keyboard interrupt (Ctrl+C)
        """
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_signal(s)),
                )
                logger.info(f"Installed signal handler for {sig.name}")
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                signal.signal(sig, self._sync_signal_handler)
                logger.info(f"Installed sync signal handler for {sig.name}")

    def _sync_signal_handler(self, signum: int, frame: Any) -> None:
        """Synchronous signal handler for Windows compatibility."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self._is_shutting_down = True
        self._shutdown_event.set()

    async def _handle_signal(self, sig: signal.Signals) -> None:
        """Handle shutdown signal asynchronously."""
        logger.info(
            f"Received {sig.name}, initiating graceful shutdown...",
            extra={"signal": sig.name},
        )
        await self.shutdown()

    async def increment_connections(self) -> None:
        """Increment active connection counter."""
        async with self._lock:
            self._active_connections += 1

    async def decrement_connections(self) -> None:
        """Decrement active connection counter."""
        async with self._lock:
            self._active_connections -= 1

    async def wait_for_drain(self) -> None:
        """Wait for in-flight requests to complete."""
        if self._active_connections <= 0:
            return

        logger.info(
            f"Waiting for {self._active_connections} active connections to drain...",
            extra={"active_connections": self._active_connections},
        )

        start_time = asyncio.get_event_loop().time()
        while self._active_connections > 0:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= self.drain_timeout:
                logger.warning(
                    f"Drain timeout reached with {self._active_connections} connections remaining",
                    extra={
                        "remaining_connections": self._active_connections,
                        "timeout": self.drain_timeout,
                    },
                )
                break
            await asyncio.sleep(0.1)

        logger.info("Connection drain completed")

    async def shutdown(self) -> None:
        """Execute graceful shutdown sequence.

        Steps:
        1. Mark as shutting down (reject new requests)
        2. Wait for in-flight requests to drain
        3. Run cleanup hooks in reverse order
        4. Signal completion
        """
        if self._is_shutting_down:
            logger.debug("Shutdown already in progress")
            return

        self._is_shutting_down = True
        logger.info(
            "Starting graceful shutdown sequence",
            extra={
                "shutdown_timeout": self.shutdown_timeout,
                "drain_timeout": self.drain_timeout,
                "cleanup_hooks": len(self._cleanup_hooks),
            },
        )

        try:
            # Step 1: Wait for connections to drain
            await asyncio.wait_for(
                self.wait_for_drain(),
                timeout=self.drain_timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Connection drain timed out")

        # Step 2: Run cleanup hooks (reverse order)
        cleanup_errors: list[tuple[str, Exception]] = []
        for hook in reversed(self._cleanup_hooks):
            hook_name = hook.__name__
            try:
                logger.debug(f"Running cleanup hook: {hook_name}")
                await asyncio.wait_for(
                    hook(),
                    timeout=self.shutdown_timeout / max(len(self._cleanup_hooks), 1),
                )
                logger.info(f"Cleanup hook completed: {hook_name}")
            except asyncio.TimeoutError:
                logger.error(f"Cleanup hook timed out: {hook_name}")
                cleanup_errors.append((hook_name, asyncio.TimeoutError()))
            except Exception as e:
                logger.exception(f"Cleanup hook failed: {hook_name}")
                cleanup_errors.append((hook_name, e))

        # Step 3: Signal completion
        self._shutdown_event.set()

        if cleanup_errors:
            logger.warning(
                f"Shutdown completed with {len(cleanup_errors)} cleanup errors",
                extra={"errors": [name for name, _ in cleanup_errors]},
            )
        else:
            logger.info("Graceful shutdown completed successfully")

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown to complete. Useful for tests."""
        await self._shutdown_event.wait()


# Global shutdown manager instance
_shutdown_manager: GracefulShutdown | None = None


def get_shutdown_manager() -> GracefulShutdown:
    """Get or create the global shutdown manager."""
    global _shutdown_manager
    if _shutdown_manager is None:
        _shutdown_manager = GracefulShutdown()
    return _shutdown_manager


@asynccontextmanager
async def graceful_lifespan(
    app: Any,
    *,
    cleanup_hooks: list[Callable[[], Coroutine[Any, Any, None]]] | None = None,
    shutdown_timeout: float = 30.0,
    drain_timeout: float = 10.0,
) -> AsyncGenerator[dict[str, Any], None]:
    """FastAPI lifespan context manager with graceful shutdown.

    Usage:
        from fastapi import FastAPI
        from prep.observability.shutdown import graceful_lifespan

        async def cleanup_db():
            await db.close()

        app = FastAPI(lifespan=lambda app: graceful_lifespan(
            app,
            cleanup_hooks=[cleanup_db]
        ))

    Args:
        app: FastAPI application instance
        cleanup_hooks: List of async cleanup functions
        shutdown_timeout: Maximum shutdown time
        drain_timeout: Maximum drain time

    Yields:
        State dict that can be accessed via request.state
    """
    shutdown_manager = GracefulShutdown(
        shutdown_timeout=shutdown_timeout,
        drain_timeout=drain_timeout,
    )

    # Register provided cleanup hooks
    if cleanup_hooks:
        for hook in cleanup_hooks:
            shutdown_manager.register_cleanup(hook)

    # Install signal handlers
    shutdown_manager.install_signal_handlers()

    logger.info(
        "Application startup complete",
        extra={
            "cleanup_hooks_registered": len(cleanup_hooks or []),
            "shutdown_timeout": shutdown_timeout,
            "drain_timeout": drain_timeout,
        },
    )

    try:
        yield {"shutdown_manager": shutdown_manager}
    finally:
        await shutdown_manager.shutdown()


# Common cleanup functions for typical dependencies


async def cleanup_database_pool() -> None:
    """Clean up SQLAlchemy database connection pool."""
    try:
        # Import dynamically to avoid circular imports
        from prep.database import get_session_factory

        session_factory = get_session_factory()
        if session_factory is not None:
            # Dispose of the engine via the session factory's bind
            engine = session_factory.kw.get("bind")
            if engine is not None:
                await asyncio.to_thread(engine.dispose)
                logger.info("Database connection pool disposed")
    except ImportError:
        logger.debug("Database module not available for cleanup")
    except Exception as e:
        logger.error(f"Error disposing database pool: {e}")


async def cleanup_redis_connections() -> None:
    """Clean up Redis connection pools."""
    try:
        import redis.asyncio as aioredis

        # Note: redis-py 4.x+ uses individual client close methods
        # This is a placeholder - actual cleanup should be done
        # by closing specific client instances
        logger.info("Redis cleanup initiated (clients should be closed individually)")
        _ = aioredis  # Silence unused import warning
        # Add minimal async operation for type checker
        await asyncio.sleep(0)
    except ImportError:
        logger.debug("Redis module not available for cleanup")
    except Exception as e:
        logger.error(f"Error closing Redis connections: {e}")


async def cleanup_http_clients() -> None:
    """Clean up HTTP client sessions."""
    try:
        # httpx clients should be closed by their owners
        # This function serves as a hook point for custom cleanup
        logger.info("HTTP client cleanup hook called")
        # Add minimal async operation for type checker
        await asyncio.sleep(0)
    except Exception as e:
        logger.error(f"Error cleaning up HTTP clients: {e}")


__all__ = [
    "GracefulShutdown",
    "cleanup_database_pool",
    "cleanup_http_clients",
    "cleanup_redis_connections",
    "get_shutdown_manager",
    "graceful_lifespan",
]
