"""Compatibility shim exposing the core ``reg_horizon_engine`` package."""
from __future__ import annotations

import importlib
import sys
from types import ModuleType

_core_module: ModuleType | None = None


def _load_core() -> ModuleType:
    global _core_module
    if _core_module is None:
        _core_module = importlib.import_module(".reg_horizon_engine", __name__)
        sys.modules.setdefault("reg_horizon_engine", _core_module)
    return _core_module


def __getattr__(name: str):
    module = _load_core()
    return getattr(module, name)


def __dir__() -> list[str]:
    module = _load_core()
    return sorted(set(__all__ + list(module.__dict__)))


__all__ = ["_load_core"]
