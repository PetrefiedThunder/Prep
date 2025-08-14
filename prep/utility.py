"""Utility helpers for the Prep package."""

from __future__ import annotations

import json
from pathlib import Path


def util_func(path: Path | str) -> dict:
    """Load a JSON configuration file.

    Parameters
    ----------
    path:
        Location of the JSON configuration file.

    Returns
    -------
    dict
        Parsed configuration data.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    json.JSONDecodeError
        If the file content is not valid JSON.
    """

    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Config file '{file_path}' not found")

    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)
