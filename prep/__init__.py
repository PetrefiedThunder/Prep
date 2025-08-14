"""Prep package initialization utilities."""

from __future__ import annotations

import os
from pathlib import Path

from .utility import util_func


def initialize(config_path: Path | str | None = None) -> dict:
    """Initialize the Prep package by loading configuration data.

    Parameters
    ----------
    config_path:
        Optional path to a JSON configuration file. If ``None``, the
        ``PREP_CONFIG`` environment variable is checked, defaulting to
        ``'prep_config.json'`` if unset.

    Returns
    -------
    dict
        The loaded configuration mapping.
    """

    if config_path is None:
        config_path = os.getenv("PREP_CONFIG", "prep_config.json")

    return util_func(config_path)
