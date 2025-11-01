"""Tests for ETL fee schedule validation helpers."""

from __future__ import annotations

import importlib.util
import pkgutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

Validator = Callable[[], dict[str, Any]]
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SCRAPER_ROOT = REPO_ROOT / "etl" / "scrapers"
SCRAPER_PREFIX = "etl.scrapers"


def _ensure_package_stubs() -> None:
    if "etl" not in sys.modules:
        etl_pkg = ModuleType("etl")
        etl_pkg.__path__ = [str(REPO_ROOT / "etl")]
        sys.modules["etl"] = etl_pkg
    if SCRAPER_PREFIX not in sys.modules:
        scrapers_pkg = ModuleType(SCRAPER_PREFIX)
        scrapers_pkg.__path__ = [str(SCRAPER_ROOT)]
        sys.modules[SCRAPER_PREFIX] = scrapers_pkg


def _collect_validators() -> list[Validator]:
    """Gather fee schedule validators from the scraper modules."""

    _ensure_package_stubs()
    validators: list[Validator] = []
    for module_info in pkgutil.iter_modules([str(SCRAPER_ROOT)], SCRAPER_PREFIX + "."):
        spec = module_info.module_finder.find_spec(module_info.name)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_info.name] = module
        spec.loader.exec_module(module)
        for attr_name in dir(module):
            if not attr_name.startswith("validate_fee_schedule_"):
                continue
            candidate = getattr(module, attr_name)
            if callable(candidate):
                validators.append(candidate)  # type: ignore[arg-type]
    return validators


def _collect_results() -> list[dict[str, Any]]:
    validators = _collect_validators()
    assert validators, "expected at least one fee schedule validator"
    results: list[dict[str, Any]] = []
    for validator in validators:
        result = validator()
        assert isinstance(result, dict), f"validator {validator.__name__} returned non-dict"
        result.setdefault("validator", validator.__name__)
        results.append(result)
    return results


def test_fee_schedules_are_valid() -> None:
    """Each discovered fee schedule validator should report success."""

    for result in _collect_results():
        assert result.get("valid") is True, f"validator {result['validator']} reported failure"
        totals = result.get("totals", {})
        assert isinstance(totals, dict)
        for key in ("fixed", "variable"):
            value = totals.get(key, 0.0)
            assert value >= 0, f"total {key} is negative for {result['validator']}"


def test_tiered_schedules_present_when_expected() -> None:
    """Validators should surface tiered fee data when the schedule implies it."""

    tiered_expectations_found = False
    for result in _collect_results():
        details = result.get("details", [])
        assert isinstance(details, list)
        for entry in details:
            tiers_expected = bool(entry.get("tiers_expected"))
            tiers = entry.get("tiers", [])
            if tiers_expected:
                tiered_expectations_found = True
                assert entry.get("tiers_present") is True
                assert tiers, "tiers expected but missing"
                for tier in tiers:
                    fee = tier.get("fee")
                    if fee is not None:
                        assert fee >= 0, "tier fee must be non-negative"
            assert not entry.get("issues"), f"unexpected issues for {entry}"
    assert tiered_expectations_found, "no tiered expectations were reported"
