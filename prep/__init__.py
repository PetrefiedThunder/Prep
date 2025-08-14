"""Prep package initialization utilities.

This module provides a simple helper for loading configuration data from a
JSON file.  It replaces the previous placeholder that merely returned ``True``
so that the package offers meaningful behaviour for consumers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def initialize(config_path: str) -> Dict[str, Any]:
    """Load configuration from ``config_path``.

    Parameters
    ----------
    config_path:
        Path to a JSON configuration file.

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

    path = Path(config_path)
    with path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)
