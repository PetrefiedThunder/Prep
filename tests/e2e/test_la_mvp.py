"""End-to-end scaffolding test for LA MVP."""
from __future__ import annotations

import importlib


SERVICE_MODULES = [
    "apps.api_gateway.app",
    "apps.bookings.repository",
    "apps.city_regulatory_service.main",
    "apps.compliance_service.main",
    "apps.federal_regulatory_service.main",
]


def test_services_importable() -> None:
    for module_name in SERVICE_MODULES:
        module = importlib.import_module(module_name)
        assert module is not None
