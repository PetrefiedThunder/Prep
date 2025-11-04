"""ASGI entrypoint for hosting platforms that import `main:app`."""

from __future__ import annotations

from api.index import create_app

app = create_app()

__all__ = ["app"]
