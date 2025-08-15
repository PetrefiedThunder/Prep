"""Prep package initialization utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from .utility import util_func

_CONFIG: Dict[str, Any] | None = None

def initialize(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Load configuration data from a JSON file.

    Parameters
    ----------
    config_path:
        Optional path to a JSON configuration file. If ``None``, the
        ``PREP_CONFIG`` environment variable is checked, defaulting to
        ``'prep_config.json'`` if unset.

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
    global _CONFIG

    if config_path is None:
        if _CONFIG is not None:
            return _CONFIG
        config_path = os.getenv("PREP_CONFIG", "prep_config.json")

    _CONFIG = util_func(config_path)
    return _CONFIG
