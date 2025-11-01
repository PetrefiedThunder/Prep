"""Fee schedule validation for San Francisco scraper outputs."""

from __future__ import annotations

from typing import Any, Iterable

from apps.city_regulatory_service.src.adapters import SanFranciscoAdapter


def _collect_requirements() -> Iterable[dict[str, Any]]:
    """Return all San Francisco regulatory requirements."""

    return SanFranciscoAdapter.get_all_requirements()


def validate_fee_schedule_san_francisco() -> dict[str, Any]:
    """Validate San Francisco fee schedules extracted by the scraper."""

    requirements = list(_collect_requirements())
    details: list[dict[str, Any]] = []
    fixed_total = 0.0
    variable_total = 0.0
    tier_count = 0
    has_tier_expectations = False

    for requirement in requirements:
        fee_data = requirement.get("fee_structure")
        if not isinstance(fee_data, dict):
            continue

        amount = fee_data.get("amount")
        schedule = str(fee_data.get("schedule", "")).strip()
        tiers = fee_data.get("tiers") if isinstance(fee_data.get("tiers"), list) else []
        issues: list[str] = []

        if isinstance(amount, (int, float)):
            if amount < 0:
                issues.append("negative fee amount")
            else:
                fixed_total += float(amount)
        elif amount not in (None, ""):
            issues.append("invalid fee amount type")

        tiers_expected = any(
            keyword in schedule.lower() for keyword in ("variable", "gross receipts", "per seat")
        )
        tiers_present = bool(tiers)
        if tiers_expected:
            has_tier_expectations = True
        if tiers_expected and not tiers_present:
            issues.append("expected tiered pricing data")

        for tier in tiers:
            fee_value = tier.get("fee")
            if isinstance(fee_value, (int, float)):
                if fee_value < 0:
                    issues.append("tier fee is negative")
                else:
                    variable_total += float(fee_value)
            elif fee_value not in (None, ""):
                issues.append("tier fee has invalid type")

        tier_count += len(tiers)

        details.append(
            {
                "requirement_id": requirement.get("requirement_id"),
                "label": requirement.get("requirement_label"),
                "schedule": schedule,
                "amount": amount if isinstance(amount, (int, float)) else None,
                "tiers_expected": tiers_expected,
                "tiers_present": tiers_present,
                "tiers": tiers,
                "issues": issues,
            }
        )

    valid = all(not entry["issues"] for entry in details)
    return {
        "jurisdiction": "San Francisco, CA",
        "valid": valid,
        "details": details,
        "has_tier_expectations": has_tier_expectations,
        "totals": {
            "fixed": fixed_total,
            "variable": variable_total,
            "tier_count": tier_count,
        },
    }


__all__ = ["validate_fee_schedule_san_francisco"]
