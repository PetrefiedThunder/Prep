#!/usr/bin/env python3
"""CLI for validating fee schedules extracted by ETL scrapers."""

from __future__ import annotations

import importlib.util
import json
import pkgutil
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from types import ModuleType
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

Validator = Callable[[], dict[str, Any]]
SCRAPER_ROOT = REPO_ROOT / "etl" / "scrapers"
SCRAPER_PREFIX = "etl.scrapers"


def _ensure_package_stubs() -> None:
    """Create lightweight package modules so submodules import cleanly."""

    if "etl" not in sys.modules:
        etl_pkg = ModuleType("etl")
        etl_pkg.__path__ = [str(REPO_ROOT / "etl")]
        sys.modules["etl"] = etl_pkg
    if SCRAPER_PREFIX not in sys.modules:
        scrapers_pkg = ModuleType(SCRAPER_PREFIX)
        scrapers_pkg.__path__ = [str(SCRAPER_ROOT)]
        sys.modules[SCRAPER_PREFIX] = scrapers_pkg


def _iter_scraper_modules() -> Iterable[ModuleType]:
    """Yield scraper modules without importing the broader ``etl`` package."""

    _ensure_package_stubs()
    for module_info in pkgutil.iter_modules([str(SCRAPER_ROOT)], SCRAPER_PREFIX + "."):
        spec = module_info.module_finder.find_spec(module_info.name)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_info.name] = module
        spec.loader.exec_module(module)
        yield module


def _discover_validators() -> list[Validator]:
    """Return callable fee schedule validators from scraper modules."""

    validators: list[Validator] = []
    for module in _iter_scraper_modules():
        for attr_name in dir(module):
            if not attr_name.startswith("validate_fee_schedule_"):
                continue
            candidate = getattr(module, attr_name)
            if callable(candidate):
                validators.append(candidate)  # type: ignore[arg-type]
    return validators


def _run_validator(validator: Validator) -> dict[str, Any]:
    """Execute a validator and normalize its result."""

    result = validator()
    if not isinstance(result, dict):
        raise TypeError(
            f"Validator {validator.__name__} returned non-dict result of type {type(result)!r}"
        )
    result.setdefault("validator", validator.__name__)
    return result


def main(argv: Iterable[str] | None = None) -> int:
    """Run fee schedule validation and emit JSON output."""

    validators = _discover_validators()
    if not validators:
        print("No fee schedule validators discovered.", file=sys.stderr)
        return 1

    results: list[dict[str, Any]] = []
    overall_success = True
    for validator in validators:
        try:
            result = _run_validator(validator)
        except Exception as exc:  # pragma: no cover - defensive output
            overall_success = False
            results.append(
                {
                    "validator": validator.__name__,
                    "valid": False,
                    "error": str(exc),
                }
            )
            continue

        results.append(result)
        if not result.get("valid", False):
            overall_success = False

    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
