"""Server package for Prep webhook handlers."""

from .main import app, get_settings

__all__ = ["app", "get_settings"]
"""FastAPI webhook receiver demo application."""

from .main import app

__all__ = ["app"]
