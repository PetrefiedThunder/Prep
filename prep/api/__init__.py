"""API router package for the Prep platform.

Modules are intentionally not imported eagerly to avoid pulling in optional
dependencies when only a subset of the API is used (e.g., during unit tests).
"""

from importlib import import_module

__all__ = [
    "admin_regulatory",
    "auth",
    "bookings",
    "deliveries",
    "integrations",
    "kitchens",
    "orders",
    "regulatory",
    "search",
]


def __getattr__(name: str):
    if name in __all__:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module '{__name__}' has no attribute {name!r}")
