"""Tests for the :mod:`prep.admin` package exports."""

from __future__ import annotations

import importlib
import sys

import pytest


def _reload_admin_module() -> object:
    sys.modules.pop("prep.admin", None)
    return importlib.import_module("prep.admin")


@pytest.mark.parametrize(
    "env_value,expected_module", [(None, "prep.admin.api"), ("1", "prep.admin.dashboard_db_api")]
)
def test_router_selection(
    monkeypatch: pytest.MonkeyPatch, env_value: str | None, expected_module: str
) -> None:
    monkeypatch.delenv("PREP_USE_DB_ADMIN_ROUTER", raising=False)
    if env_value is not None:
        monkeypatch.setenv("PREP_USE_DB_ADMIN_ROUTER", env_value)

    admin_module = _reload_admin_module()
    route_modules = {route.endpoint.__module__ for route in admin_module.router.routes}

    assert expected_module in route_modules
    alternate_module = (
        "prep.admin.dashboard_db_api" if expected_module == "prep.admin.api" else "prep.admin.api"
    )
    assert alternate_module not in route_modules


def test_certification_and_analytics_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PREP_USE_DB_ADMIN_ROUTER", raising=False)
    admin_module = _reload_admin_module()

    assert hasattr(admin_module, "certification_router")
    assert hasattr(admin_module, "get_certification_verification_api")
    assert hasattr(admin_module, "get_analytics_service")
