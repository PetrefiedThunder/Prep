"""FastAPI entrypoint for hosting platforms expecting a `main.py` module."""

from __future__ import annotations

from api.index import create_app

app = create_app()

__all__ = ["app"]
