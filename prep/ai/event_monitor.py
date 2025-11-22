"""Event monitoring system for repository changes.

This module provides event monitoring capabilities for agents to observe
file changes, git events, and other repository activities.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of repository events."""

    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    FILE_RENAMED = "file_renamed"
    DIRECTORY_CREATED = "directory_created"
    DIRECTORY_DELETED = "directory_deleted"
    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"
    GIT_PR_OPENED = "git_pr_opened"
    GIT_PR_UPDATED = "git_pr_updated"
    DEPENDENCY_UPDATED = "dependency_updated"
    TEST_FAILED = "test_failed"
    BUILD_FAILED = "build_failed"
    CUSTOM = "custom"


@dataclass
class RepositoryEvent:
    """Represents an event in the repository."""

    event_id: str
    event_type: EventType
    timestamp: datetime
    file_path: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


EventHandler = Callable[[RepositoryEvent], Any]


class EventMonitor:
    """Monitors repository for changes and notifies registered handlers.

    The EventMonitor watches for file system changes and other repository
    events, dispatching them to registered event handlers (typically agents).
    """

    def __init__(self, root_dir: str | Path = ".") -> None:
        """Initialize the event monitor.

        Args:
            root_dir: Root directory to monitor
        """
        self.root_dir = Path(root_dir).resolve()
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._file_hashes: dict[str, str] = {}
        self._running = False
        self._monitor_task: asyncio.Task | None = None
        self._event_queue: asyncio.Queue[RepositoryEvent] = asyncio.Queue()
        self._exclude_patterns: list[str] = [
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
            "*.pyc",
            ".DS_Store",
        ]

    def register_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """Register an event handler for a specific event type.

        Args:
            event_type: The type of event to handle
            handler: The callback function to invoke when the event occurs
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(f"Registered handler for {event_type.value}")

    def unregister_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """Unregister an event handler.

        Args:
            event_type: The type of event
            handler: The callback function to remove
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.info(f"Unregistered handler for {event_type.value}")

    def _should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from monitoring.

        Args:
            path: The path to check

        Returns:
            True if the path should be excluded
        """
        path_str = str(path)
        for pattern in self._exclude_patterns:
            if pattern.startswith("*"):
                # Wildcard pattern
                if path_str.endswith(pattern[1:]):
                    return True
            elif pattern in path_str:
                return True
        return False

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hex digest of the file's SHA256 hash
        """
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.debug(f"Could not hash {file_path}: {e}")
            return ""

    async def _scan_directory(self) -> dict[str, str]:
        """Scan directory and return file hashes.

        Returns:
            Dictionary mapping file paths to their hashes
        """
        file_hashes = {}

        for path in self.root_dir.rglob("*"):
            if path.is_file() and not self._should_exclude(path):
                try:
                    rel_path = str(path.relative_to(self.root_dir))
                    file_hash = self._compute_file_hash(path)
                    file_hashes[rel_path] = file_hash
                except Exception as e:
                    logger.debug(f"Error scanning {path}: {e}")

        return file_hashes

    async def _detect_changes(self) -> list[RepositoryEvent]:
        """Detect changes in the repository.

        Returns:
            List of detected events
        """
        events: list[RepositoryEvent] = []
        current_hashes = await self._scan_directory()

        # Detect new and modified files
        for file_path, file_hash in current_hashes.items():
            if file_path not in self._file_hashes:
                # New file
                event = RepositoryEvent(
                    event_id=str(uuid4()),
                    event_type=EventType.FILE_CREATED,
                    timestamp=datetime.utcnow(),
                    file_path=file_path,
                )
                events.append(event)
            elif self._file_hashes[file_path] != file_hash:
                # Modified file
                event = RepositoryEvent(
                    event_id=str(uuid4()),
                    event_type=EventType.FILE_MODIFIED,
                    timestamp=datetime.utcnow(),
                    file_path=file_path,
                )
                events.append(event)

        # Detect deleted files
        for file_path in self._file_hashes:
            if file_path not in current_hashes:
                event = RepositoryEvent(
                    event_id=str(uuid4()),
                    event_type=EventType.FILE_DELETED,
                    timestamp=datetime.utcnow(),
                    file_path=file_path,
                )
                events.append(event)

        # Update file hashes
        self._file_hashes = current_hashes

        return events

    async def _dispatch_event(self, event: RepositoryEvent) -> None:
        """Dispatch an event to registered handlers.

        Args:
            event: The event to dispatch
        """
        handlers = self._handlers.get(event.event_type, [])

        if not handlers:
            logger.debug(f"No handlers for event type {event.event_type.value}")
            return

        logger.info(f"Dispatching {event.event_type.value} event for {event.file_path}")

        # Call all handlers
        for handler in handlers:
            try:
                result = handler(event)
                # Handle both sync and async handlers
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Handler error for {event.event_type.value}: {e}")

    async def _monitor_loop(self, poll_interval: float = 2.0) -> None:
        """Main monitoring loop.

        Args:
            poll_interval: Time in seconds between directory scans
        """
        # Initial scan
        self._file_hashes = await self._scan_directory()
        logger.info(f"Initial scan found {len(self._file_hashes)} files")

        while self._running:
            try:
                # Detect changes
                events = await self._detect_changes()

                # Dispatch events
                for event in events:
                    await self._dispatch_event(event)

                # Wait before next scan
                await asyncio.sleep(poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(poll_interval)

    async def start(self, poll_interval: float = 2.0) -> None:
        """Start monitoring the repository.

        Args:
            poll_interval: Time in seconds between directory scans
        """
        if self._running:
            logger.warning("Event monitor already running")
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(poll_interval))
        logger.info(f"Event monitor started (polling every {poll_interval}s)")

    async def stop(self) -> None:
        """Stop monitoring the repository."""
        if not self._running:
            return

        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Event monitor stopped")

    async def emit_custom_event(
        self,
        event_type: EventType,
        file_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Emit a custom event manually.

        Args:
            event_type: Type of the event
            file_path: Optional file path associated with the event
            details: Optional details dictionary
        """
        event = RepositoryEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            timestamp=datetime.utcnow(),
            file_path=file_path,
            details=details or {},
        )

        await self._dispatch_event(event)


__all__ = [
    "EventMonitor",
    "RepositoryEvent",
    "EventType",
    "EventHandler",
]
