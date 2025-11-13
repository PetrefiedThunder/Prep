"""Lightweight aiosqlite shim for test environments."""

from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Iterable
from functools import partial
from typing import Any

__all__ = [
    "connect",
    "Connection",
    "Cursor",
    "Error",
    "OperationalError",
    "DatabaseError",
    "IntegrityError",
    "NotSupportedError",
    "ProgrammingError",
    "sqlite_version",
    "sqlite_version_info",
]

Error = sqlite3.Error
DatabaseError = sqlite3.DatabaseError
IntegrityError = sqlite3.IntegrityError
NotSupportedError = sqlite3.NotSupportedError
OperationalError = sqlite3.OperationalError
ProgrammingError = sqlite3.ProgrammingError
sqlite_version = sqlite3.sqlite_version
sqlite_version_info = sqlite3.sqlite_version_info


class Cursor:
    """Async cursor wrapper backed by ``sqlite3``."""

    def __init__(self, cursor: sqlite3.Cursor, loop: asyncio.AbstractEventLoop) -> None:
        self._cursor = cursor
        self._loop = loop

    async def execute(self, sql: str, parameters: Iterable[Any] | None = None) -> Cursor:
        await self._loop.run_in_executor(None, self._cursor.execute, sql, parameters or ())
        return self

    async def executemany(self, sql: str, seq_of_parameters: Iterable[Iterable[Any]]) -> Cursor:
        await self._loop.run_in_executor(None, self._cursor.executemany, sql, seq_of_parameters)
        return self

    async def fetchone(self) -> Any:
        return await self._loop.run_in_executor(None, self._cursor.fetchone)

    async def fetchall(self) -> list[Any]:
        return await self._loop.run_in_executor(None, self._cursor.fetchall)

    async def fetchmany(self, size: int | None = None) -> list[Any]:
        if size is None:
            return await self._loop.run_in_executor(None, self._cursor.fetchmany)
        return await self._loop.run_in_executor(None, self._cursor.fetchmany, size)

    async def close(self) -> None:
        await self._loop.run_in_executor(None, self._cursor.close)

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def description(self) -> Any:
        return self._cursor.description

    @property
    def lastrowid(self) -> Any:
        return self._cursor.lastrowid


class Connection:
    """Async connection wrapper compatible with SQLAlchemy's aiosqlite dialect."""

    def __init__(self, conn: sqlite3.Connection, loop: asyncio.AbstractEventLoop) -> None:
        self._conn = conn
        self._loop = loop

    async def cursor(self) -> Cursor:
        cursor = await self._loop.run_in_executor(None, self._conn.cursor)
        return Cursor(cursor, self._loop)

    async def execute(self, sql: str, parameters: Iterable[Any] | None = None) -> Cursor:
        cursor = await self.cursor()
        await cursor.execute(sql, parameters)
        return cursor

    async def executemany(self, sql: str, seq_of_parameters: Iterable[Iterable[Any]]) -> Cursor:
        cursor = await self.cursor()
        await cursor.executemany(sql, seq_of_parameters)
        return cursor

    async def executescript(self, script: str) -> None:
        await self._loop.run_in_executor(None, self._conn.executescript, script)

    async def commit(self) -> None:
        await self._loop.run_in_executor(None, self._conn.commit)

    async def rollback(self) -> None:
        await self._loop.run_in_executor(None, self._conn.rollback)

    async def create_function(self, *args: Any, **kwargs: Any) -> None:
        factory = partial(self._conn.create_function, *args, **kwargs)
        await self._loop.run_in_executor(None, factory)

    async def close(self) -> None:
        await self._loop.run_in_executor(None, self._conn.close)

    async def __aenter__(self) -> Connection:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        if exc:
            await self.rollback()
        await self.close()

    @property
    def row_factory(self) -> Any:
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, value: Any) -> None:
        self._conn.row_factory = value

    @property
    def text_factory(self) -> Any:
        return self._conn.text_factory

    @text_factory.setter
    def text_factory(self, value: Any) -> None:
        self._conn.text_factory = value


class _ConnectAwaitable:
    """Awaitable wrapper that exposes a ``daemon`` attribute like a thread."""

    def __init__(
        self, loop: asyncio.AbstractEventLoop, database: str, kwargs: dict[str, Any]
    ) -> None:
        self._loop = loop
        self._database = database
        self._kwargs = kwargs
        self.daemon = False

    def __await__(self):  # type: ignore[override]
        return self._run().__await__()

    async def _run(self) -> Connection:
        factory = partial(sqlite3.connect, self._database, **self._kwargs)
        conn = await self._loop.run_in_executor(None, factory)
        return Connection(conn, self._loop)


def connect(database: str, **kwargs: Any) -> _ConnectAwaitable:
    """Async connect wrapper for ``sqlite3.connect`` returning an awaitable."""

    loop = asyncio.get_running_loop()
    kwargs["check_same_thread"] = False
    return _ConnectAwaitable(loop, database, kwargs)
