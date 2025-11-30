#!/usr/bin/env python3
"""
MVP Endpoint Validation Script

Validates that all MVP-critical endpoints are registered in the FastAPI gateway.
This script does NOT require a running database - it only inspects the route table.

Usage:
    python scripts/validate_mvp_endpoints.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from typing import Any

# Set minimal environment for import
import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://localhost/prep")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-key-for-validation-only")

from api.index import create_app


def extract_routes(app: Any) -> dict[str, list[dict[str, Any]]]:
    """Extract all routes from FastAPI app organized by prefix."""
    routes_by_prefix: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for route in app.routes:
        # Skip non-API routes
        if not hasattr(route, "methods") or not hasattr(route, "path"):
            continue

        # Skip health check and docs
        if route.path in ("/healthz", "/docs", "/openapi.json", "/redoc"):
            continue

        methods = list(route.methods - {"HEAD", "OPTIONS"})  # Remove common non-functional methods
        if not methods:
            continue

        # Determine prefix for grouping
        path_parts = route.path.split("/")
        if len(path_parts) >= 3:
            prefix = "/" + path_parts[1] + "/" + path_parts[2]
        elif len(path_parts) >= 2:
            prefix = "/" + path_parts[1]
        else:
            prefix = "/"

        route_info = {
            "path": route.path,
            "methods": sorted(methods),
            "name": getattr(route, "name", "unknown"),
        }

        routes_by_prefix[prefix].append(route_info)

    return dict(routes_by_prefix)


def check_mvp_endpoints(routes_by_prefix: dict[str, list[dict[str, Any]]]) -> tuple[list[str], list[str]]:
    """Check for required MVP endpoints and return found/missing lists."""

    # Define MVP-critical endpoints
    mvp_endpoints = {
        # Authentication
        "/api/v1/platform/users/register": ["POST"],
        "/api/v1/platform/auth/login": ["POST"],
        "/api/v1/platform/auth/refresh": ["POST"],
        "/api/v1/auth/token": ["POST"],

        # Kitchen Listings
        "/kitchens": ["GET", "POST"],
        "/kitchens/{kitchen_id}": ["GET"],
        "/kitchens/{kitchen_id}/compliance": ["GET"],

        # Bookings
        "/bookings": ["POST"],

        # Payments
        "/api/v1/platform/payments/intent": ["POST"],
        "/api/v1/platform/payments/checkout": ["POST"],
        "/payments/webhook": ["POST"],
        "/payments/connect": ["POST"],
    }

    # Flatten all routes for easier checking
    all_routes = []
    for routes in routes_by_prefix.values():
        all_routes.extend(routes)

    found = []
    missing = []

    for required_path, required_methods in mvp_endpoints.items():
        # Check if path exists (accounting for path parameters)
        path_found = False
        methods_found = set()

        for route in all_routes:
            route_path = route["path"]
            # Normalize path parameters for comparison
            normalized_required = required_path.replace("{kitchen_id}", "{id}").replace("{id}", "{kitchen_id}")
            normalized_route = route_path.replace("{kitchen_id}", "{id}").replace("{id}", "{kitchen_id}")

            if route_path == required_path or normalized_required == normalized_route:
                path_found = True
                methods_found.update(route["methods"])

        if path_found:
            # Check if all required methods are present
            if all(method in methods_found for method in required_methods):
                found.append(f"✅ {required_path} {required_methods}")
            else:
                missing_methods = set(required_methods) - methods_found
                found.append(f"⚠️  {required_path} (missing methods: {list(missing_methods)})")
        else:
            missing.append(f"❌ {required_path} {required_methods}")

    return found, missing


def print_route_table(routes_by_prefix: dict[str, list[dict[str, Any]]]) -> None:
    """Print organized route table."""
    print("\n" + "=" * 80)
    print("FASTAPI GATEWAY - REGISTERED ROUTES")
    print("=" * 80)

    for prefix in sorted(routes_by_prefix.keys()):
        routes = routes_by_prefix[prefix]
        print(f"\n📁 {prefix}")
        print("-" * 80)

        for route in sorted(routes, key=lambda r: (r["path"], str(r["methods"]))):
            methods_str = ", ".join(route["methods"])
            print(f"  {methods_str:12} {route['path']}")

    print("\n" + "=" * 80)


def main() -> int:
    """Main validation routine."""
    print("🔍 MVP Endpoint Validation - Phase 0")
    print("=" * 80)
    print("Loading FastAPI application...")

    try:
        app = create_app(include_full_router=True, include_legacy_mounts=True)
        print(f"✅ Application loaded successfully")
        print(f"   Title: {app.title}")
        print(f"   Version: {app.version}")
    except Exception as e:
        print(f"❌ Failed to load application: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Extract routes
    routes_by_prefix = extract_routes(app)
    total_routes = sum(len(routes) for routes in routes_by_prefix.values())
    print(f"✅ Extracted {total_routes} API routes across {len(routes_by_prefix)} prefixes")

    # Print full route table
    print_route_table(routes_by_prefix)

    # Check MVP endpoints
    print("\n" + "=" * 80)
    print("MVP CRITICAL ENDPOINTS - VALIDATION RESULTS")
    print("=" * 80)

    found, missing = check_mvp_endpoints(routes_by_prefix)

    print(f"\n✅ FOUND ({len(found)} endpoints):")
    for endpoint in found:
        print(f"  {endpoint}")

    if missing:
        print(f"\n❌ MISSING ({len(missing)} endpoints):")
        for endpoint in missing:
            print(f"  {endpoint}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total_required = len(found) + len(missing)
    coverage_pct = (len(found) / total_required * 100) if total_required > 0 else 0

    print(f"  Total MVP Endpoints Required: {total_required}")
    print(f"  Found: {len(found)}")
    print(f"  Missing: {len(missing)}")
    print(f"  Coverage: {coverage_pct:.1f}%")

    if missing:
        print("\n⚠️  WARNING: Some MVP endpoints are missing!")
        print("   Action: Review missing endpoints and add to FastAPI gateway")
        return 1
    else:
        print("\n✅ SUCCESS: All MVP endpoints are registered!")
        print("   Next Step: Test endpoints with real database")
        return 0


if __name__ == "__main__":
    sys.exit(main())
