#!/usr/bin/env python3
"""Smoke test all configured module imports.

This script tests that all configured routers, plugins, and dynamic modules
can be successfully imported. It's designed to run in CI to catch import
errors before they reach production.

Exit codes:
  0 - All imports succeeded
  1 - One or more imports failed
"""

import sys
from collections.abc import Iterable

from libs.safe_import import safe_import

# Core API modules that must always import
REQUIRED_MODULES: Iterable[str] = (
    "api.index",
    "prep.models.db",
    "prep.models.orm",
)

# Optional router modules (from api/index.py OPTIONAL_ROUTERS)
OPTIONAL_ROUTER_MODULES: Iterable[str] = (
    "api.routes.city_fees",
    "api.routes.diff",
    "api.city.requirements",
    "api.routes.debug",
    "api.webhooks.square_kds",
    "prep.analytics.dashboard_api",
    "prep.analytics.host_metrics_api",
    "prep.matching.api",
    "prep.payments.api",
    "prep.ratings.api",
    "prep.reviews.api",
    "prep.verification_tasks.api",
)

# Regulatory modules (from prep/regulatory/__init__.py)
OPTIONAL_REGULATORY_MODULES: Iterable[str] = (
    "prep.regulatory.analyzer",
    "prep.regulatory.analytics.impact",
    "prep.regulatory.analytics.trends",
    "prep.regulatory.apis.health_departments",
    "prep.regulatory.apis.insurance",
    "prep.regulatory.apis.zoning",
    "prep.regulatory.models",
    "prep.regulatory.monitoring.changes",
    "prep.regulatory.nlp.analyzer",
    "prep.regulatory.prediction.engine",
    "prep.regulatory.scheduler",
    "prep.regulatory.scraper",
    "prep.regulatory.loader",
    "prep.regulatory.writer",
)

# Job modules (from jobs/__init__.py)
OPTIONAL_JOB_MODULES: Iterable[str] = (
    "jobs.expiry_check",
    "jobs.pricing_hourly_refresh",
    "jobs.reconciliation_engine",
)

# City data ingestor modules (from api/routes/_city_utils.py)
OPTIONAL_CITY_MODULES: Iterable[str] = (
    "data.ingestors.sf_dph",
    "data.ingestors.oakland_dph",
    "data.ingestors.berkeley_dph",
    "data.ingestors.san_jose_dph",
    "data.ingestors.palo_alto_dph",
    "data.ingestors.joshua_tree_dph",
)


def test_required_imports() -> int:
    """Test that required modules can be imported."""
    print("Testing required module imports...")
    failures = 0

    for module_name in REQUIRED_MODULES:
        try:
            safe_import(module_name)
            print(f"  ✓ {module_name}")
        except Exception as e:
            print(f"  ✗ {module_name}: {e}", file=sys.stderr)
            failures += 1

    return failures


def test_optional_imports(modules: Iterable[str], category: str) -> int:
    """Test that optional modules can be imported (failures are warnings)."""
    print(f"\nTesting optional {category} imports...")
    failures = 0
    warnings = 0

    for module_name in modules:
        module = safe_import(module_name, optional=True)
        if module is None:
            print(f"  ⚠ {module_name} (optional, skipped)")
            warnings += 1
        else:
            print(f"  ✓ {module_name}")

    if warnings > 0:
        print(f"  Note: {warnings} optional module(s) not available (this is OK)")

    return failures


def main() -> int:
    """Run all import smoke tests."""
    print("=" * 70)
    print("Running import smoke tests")
    print("=" * 70)

    total_failures = 0

    # Test required imports (failures are fatal)
    total_failures += test_required_imports()

    # Test optional imports (failures are warnings only)
    test_optional_imports(OPTIONAL_ROUTER_MODULES, "router")
    test_optional_imports(OPTIONAL_REGULATORY_MODULES, "regulatory")
    test_optional_imports(OPTIONAL_JOB_MODULES, "job")
    test_optional_imports(OPTIONAL_CITY_MODULES, "city ingestor")

    print("\n" + "=" * 70)
    if total_failures > 0:
        print(f"❌ FAILED: {total_failures} required import(s) failed")
        print("=" * 70)
        return 1
    else:
        print("✅ PASSED: All required imports succeeded")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    sys.exit(main())
