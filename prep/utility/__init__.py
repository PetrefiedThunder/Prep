"""Utility helpers for the :mod:`prep` package."""

from __future__ import annotations

from typing import Any, Dict

__all__ = ["util_func"]


_NO_DEFAULT = object()


def util_func(config: Dict[str, Any], key: str, default: Any = _NO_DEFAULT) -> Any:
    """Retrieve ``key`` from ``config``.

    The ``key`` may represent a dotted path to nested dictionaries. If any
    part of the path is missing, ``default`` is returned when provided,
    otherwise a :class:`KeyError` is raised.
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
