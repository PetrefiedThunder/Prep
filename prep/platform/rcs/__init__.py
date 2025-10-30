"""Realtime Configuration Service primitives."""

from .models import ConfigEntry, ConfigRecord
from .service import create_app

__all__ = [
    "ConfigEntry",
    "ConfigRecord",
    "create_app",
]
