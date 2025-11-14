"""ASGI entrypoint for process managers expecting `run_api:app`."""

from __future__ import annotations

from api.index import create_app

app = create_app()

__all__ = ["app"]
