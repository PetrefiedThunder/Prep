"""Tests ensuring router modules remain accessible via :mod:`prep.api`."""

import sys
from importlib import import_module, reload
from types import ModuleType


def _install_stub(module_name: str) -> None:
    module = ModuleType(module_name)
    module.router = object()
    sys.modules[module_name] = module


def test_router_exports_available(monkeypatch):
    monkeypatch.setattr(
        "sqlalchemy.ext.asyncio.create_async_engine",
        lambda *args, **kwargs: object(),
    )

    for submodule in (
        "admin_regulatory",
        "auth",
        "bookings",
        "kitchens",
        "regulatory",
        "search",
    ):
        _install_stub(f"prep.api.{submodule}")

    api = reload(import_module("prep.api"))

    assert hasattr(api, "admin_regulatory")
    assert hasattr(api, "auth")
    assert hasattr(api, "bookings")
    assert hasattr(api, "kitchens")
    assert hasattr(api, "regulatory")
    assert hasattr(api, "search")
