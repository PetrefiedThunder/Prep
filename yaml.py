"""Minimal YAML stub used for loading municipal kernel fixtures in tests."""

from __future__ import annotations

import json
from typing import Any

_SAN_FRANCISCO_CONFIG: dict[str, Any] = {
    "state": "CA",
    "health_code": "§6.15 Shared Kitchen Facilities",
    "health_dept_url": "https://www.sfdph.org/dph/EH/Food/",
    "business_portal_url": "https://aca.accela.com/sfmea/",
    "permit_kinds": ["shared_kitchen", "fire", "ventilation", "health_permit"],
    "insurance": {
        "liability_min_cents": 100_000_000,
        "aggregate_min_cents": 200_000_000,
        "additional_insured_legal": "City and County of San Francisco",
        "workers_comp_required": True,
        "workers_comp_employee_threshold": 1,
    },
    "zoning": {
        "require_neighborhood_notice": True,
        "notice_radius_feet": 300,
        "notice_period_days": 30,
        "allowed_districts": ["NC-3", "NC-2", "NCT", "PDR", "CMUO"],
    },
    "fees": [
        {
            "code": "CRT",
            "display_name": "Commercial Rents Tax",
            "kind": "percent",
            "value": 0.035,
            "applies_to": ["base"],
            "citation": "SF Business and Tax Regulations Code Article 21",
            "remittance_url": "https://sftreasurer.org/business/taxes-fees/commercial-rents-tax",
        }
    ],
    "deposits": {
        "min_cents": 10_000,
        "hold_window_hours": 72,
        "refund_window_hours": 168,
    },
    "rental_limits": {
        "max_hours_per_day_per_facility": 12,
        "min_booking_hours": 2,
        "max_advance_booking_days": 180,
    },
    "sound_ordinance": {
        "quiet_hours": {"start": "22:00", "end": "06:00"},
        "max_decibels_day": 70,
        "max_decibels_night": 55,
        "citation": "SF Police Code Article 29",
    },
    "seasonal_restrictions": [],
    "waste": {
        "requires_food_waste_recycling": True,
        "requires_composting": True,
        "citation": "SF Environment Code Chapter 19",
    },
    "inspections": {
        "health": {
            "frequency_months": 12,
            "buffer_before_hours": 4,
            "buffer_after_hours": 2,
        },
        "fire": {
            "frequency_months": 12,
            "buffer_before_hours": 2,
            "buffer_after_hours": 1,
        },
    },
    "grease": {
        "interceptor_required": True,
        "max_service_interval_days": 180,
        "manifest_required": True,
    },
    "outbreak": {
        "auto_notify_threshold": 3,
        "notification_email": "ehs.complaints@sfdph.org",
        "hotline": "415-554-2500",
    },
    "complaints": {
        "noise": {
            "warning_threshold": 3,
            "window_days": 30,
            "soft_block_threshold": 5,
            "soft_block_window_days": 60,
        }
    },
    "compliance": {
        "business_registration": {"expiration_grace_days": 0},
        "health_permit": {
            "valid_statuses": ["valid"],
            "expiration_warning_days": 30,
            "facility_type_mapping": {
                "cooking_kitchen": "cooking_permit",
                "commissary_non_cooking": "commissary_permit",
                "mobile_food_commissary": "mobile_commissary_permit",
            },
        },
        "zoning": {
            "allowed_districts": ["NC-3", "NC-2", "NCT", "PDR", "CMUO"],
            "manual_review_when_unknown": True,
        },
        "fire": {
            "required_for": ["cooking_kitchen"],
            "inspection_max_age_days": 365,
        },
        "grease": {
            "required_for": ["cooking_kitchen", "commissary_non_cooking"],
            "service_interval_days": 180,
        },
        "tax": {
            "crt_rate": 0.035,
            "grt_threshold": 500_000,
            "default_tax_classification": "service_provider",
        },
    },
}


def safe_dump(data: Any, *args: Any, **kwargs: Any) -> str:
    """Minimal YAML dumper compatible with PyYAML's API."""

    return json.dumps(data, indent=2)


def safe_load(stream: Any) -> Any:
    """Minimal YAML loader compatible with PyYAML's API."""

    if hasattr(stream, "read"):
        content = stream.read()
    else:
        content = stream
    return json.loads(content)


__all__ = ["safe_load", "safe_dump", "_SAN_FRANCISCO_CONFIG"]
