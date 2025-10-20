"""Utility helpers for the :mod:`prep` package."""

from __future__ import annotations

from typing import Any, Dict


_NO_DEFAULT = object()


def util_func(config: Dict[str, Any], key: str, default: Any = _NO_DEFAULT) -> Any:
    """Retrieve ``key`` from ``config``.

    The ``key`` may represent a dotted path to nested dictionaries.  If any
    part of the path is missing, ``default`` is returned when provided,
    otherwise a :class:`KeyError` is raised.

    Parameters
    ----------
    config:
        Configuration dictionary to search.
    key:
        Dotted path whose value should be returned.
    default:
        Fallback value if ``key`` is not present.  If not provided and the key
        is missing a :class:`KeyError` is raised.

    Returns
    -------
    Any
        The located value or the provided ``default``.
    """

    current: Any = config
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            if default is not _NO_DEFAULT:
                return default
            raise KeyError(f"{key} not found in configuration")

    return current
