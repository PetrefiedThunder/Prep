"""Utility helpers for the :mod:`prep` package."""

from __future__ import annotations

from typing import Any, Dict


def util_func(config: Dict[str, Any], key: str, default: Any | None = None) -> Any:
    """Retrieve ``key`` from ``config``.

    Parameters
    ----------
    config:
        Configuration dictionary to search.
    key:
        Key whose value should be returned.
    default:
        Fallback value if ``key`` is not present.  If ``None`` and the key is
        missing a :class:`KeyError` is raised.

    Returns
    -------
    Any
        The located value or the provided ``default``.
    """

    if key in config:
        return config[key]

    if default is not None:
        return default

    raise KeyError(f"{key} not found in configuration")
