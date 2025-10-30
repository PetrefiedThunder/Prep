"""In-memory storage layer for the Realtime Configuration Service."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, Iterable, Optional

from .models import ChangeType, ConfigChange, ConfigEntry, ConfigRecord


@dataclass
class _Subscriber:
    queue: "asyncio.Queue[ConfigChange]"
    prefix: Optional[str]


class ConfigStore:
    """Simple in-memory configuration store with pub/sub semantics."""

    def __init__(self) -> None:
        self._records: Dict[str, ConfigRecord] = {}
        self._lock = asyncio.Lock()
        self._subscribers: Dict[int, _Subscriber] = {}
        self._next_subscriber_id = 0
        self._global_version = 0

    async def list(self, prefix: Optional[str] = None) -> Iterable[ConfigRecord]:
        """Return a snapshot of configuration records, optionally filtered by prefix."""

        async with self._lock:
            records = list(self._records.values())

        if prefix is None:
            return records

        return [record for record in records if record.key.startswith(prefix)]

    async def get(self, key: str) -> Optional[ConfigRecord]:
        """Fetch a single configuration record by key."""

        async with self._lock:
            return self._records.get(key)

    async def upsert(self, entry: ConfigEntry) -> ConfigRecord:
        """Insert or update a configuration entry and notify subscribers."""

        async with self._lock:
            self._global_version += 1
            record = ConfigRecord(
                **entry.model_dump(),
                version=self._global_version,
                updated_at=datetime.now(timezone.utc),
            )
            self._records[entry.key] = record

        change = ConfigChange(
            type=ChangeType.UPSERT,
            key=record.key,
            record=record,
            version=record.version,
            emitted_at=datetime.now(timezone.utc),
        )
        await self._notify(change)
        return record

    async def delete(self, key: str) -> Optional[ConfigRecord]:
        """Delete a configuration entry and notify subscribers."""

        async with self._lock:
            record = self._records.pop(key, None)
            if record is None:
                return None
            self._global_version += 1
            version = self._global_version

        change = ConfigChange(
            type=ChangeType.DELETE,
            key=key,
            record=None,
            version=version,
            emitted_at=datetime.now(timezone.utc),
        )
        await self._notify(change)
        return record

    async def _notify(self, change: ConfigChange) -> None:
        """Fan out a configuration change to interested subscribers."""

        to_remove = []
        for identifier, subscriber in list(self._subscribers.items()):
            if subscriber.prefix and not change.key.startswith(subscriber.prefix):
                continue
            try:
                subscriber.queue.put_nowait(change)
            except asyncio.QueueFull:
                # Drop slow subscribers after signalling so they can resubscribe.
                to_remove.append(identifier)
        for identifier in to_remove:
            self._subscribers.pop(identifier, None)

    @asynccontextmanager
    async def subscribe(
        self, prefix: Optional[str] = None, max_queue_size: int = 100
    ) -> AsyncIterator["asyncio.Queue[ConfigChange]"]:
        """Subscribe to change events filtered by optional key prefix."""

        queue: "asyncio.Queue[ConfigChange]" = asyncio.Queue(maxsize=max_queue_size)
        async with self._lock:
            identifier = self._next_subscriber_id
            self._next_subscriber_id += 1
            self._subscribers[identifier] = _Subscriber(queue=queue, prefix=prefix)
        try:
            yield queue
        finally:
            self._subscribers.pop(identifier, None)


__all__ = ["ConfigStore"]
