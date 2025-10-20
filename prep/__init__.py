"""Prep package initialization utilities.

This module exposes helpers for loading configuration data from a JSON file.
The loaded configuration is cached so subsequent calls without an explicit
path reuse the previous result.  When no path is provided, the
``PREP_CONFIG`` environment variable is consulted and finally falls back to a
``config.json`` file in the current working directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from . import utility

__all__ = ["initialize", "utility"]

_CONFIG: Dict[str, Any] | None = None


_CONFIG_PATH: Path | None = None


def initialize(
    config_path: str | None = None,
    *,
    force_reload: bool = False,
) -> Dict[str, Any]:
    """Load configuration from ``config_path``.

    Parameters
    ----------
    config_path:
        Path to a JSON configuration file.  If ``None`` the value of the
        ``PREP_CONFIG`` environment variable is used.  If that environment
        variable is unset it defaults to ``config.json`` in the current
        working directory.
    force_reload:
        When :data:`True`, bypass the cached configuration and reload the
        configuration from disk using the previously resolved configuration
        path.  If no configuration has been loaded yet this behaves the same
        as ``False``.

    Returns
    -------
    dict
        Parsed configuration dictionary.

    Raises
    ------
    FileNotFoundError
        If the given path does not exist.
    json.JSONDecodeError
        If the file contents are not valid JSON.
    """

    global _CONFIG, _CONFIG_PATH

    path: Path
    if config_path is None:
        if _CONFIG is not None and not force_reload:
            return _CONFIG
        if _CONFIG_PATH is not None:
            path = _CONFIG_PATH
        else:
            path = Path(os.environ.get("PREP_CONFIG", "config.json"))
    else:
        path = Path(config_path)

    with path.open("r", encoding="utf-8") as config_file:
        _CONFIG = json.load(config_file)

    _CONFIG_PATH = path
    return _CONFIG
