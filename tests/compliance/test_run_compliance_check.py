from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict


def iso(days_offset: int) -> str:
    value = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=days_offset)
    return value.isoformat().replace("+00:00", "Z")


def build_payload() -> Dict[str, Any]:
    return {
        "license_info": {
            "license_number": "VALID-CLI-1",
            "status": "active",
            "expiration_date": iso(180),
        },
        "inspection_history": [
            {
                "inspection_date": iso(-30),
                "overall_score": 96,
                "violations": [],
                "establishment_closed": False,
            }
        ],
        "certifications": [
            {"type": "ServSafe Manager", "status": "active"},
            {"type": "Allergen Awareness", "status": "active"},
        ],
        "equipment": [
            {
                "type": "refrigeration",
                "commercial_grade": True,
                "nsf_certified": True,
                "photo_url": "https://example.com/fridge.jpg",
            },
            {
                "type": "handwashing_station",
                "commercial_grade": True,
                "nsf_certified": True,
                "photo_url": "https://example.com/sink.jpg",
            },
        ],
        "insurance": {
            "policy_number": "CLI-INS-1",
            "expiration_date": iso(120),
        },
        "photos": [
            {"url": "https://example.com/photo1.jpg"},
            {"url": "https://example.com/photo2.jpg"},
            {"url": "https://example.com/photo3.jpg"},
        ],
        "pest_control_records": [
            {"service_date": iso(-45)},
        ],
        "cleaning_logs": [
            {"date": iso(-7)},
        ],
    }


def test_cli_accepts_stdin_and_emits_raw_report() -> None:
    payload = build_payload()
    result = subprocess.run(
        [sys.executable, "-m", "prep.compliance.run_compliance_check"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )

    output = json.loads(result.stdout.strip())

    assert output["status"] == "success"
    assert output["can_accept_bookings"] is True
    assert output["violations_found"] == []
    assert abs(output["overall_compliance_score"] - 1.0) < 1e-9

    badge = output["safety_badge"]
    assert badge["can_accept_bookings"] is True

    raw_report = output["raw_report"]
    assert raw_report["safety_badge"]["can_accept_bookings"] == output["can_accept_bookings"]
    assert raw_report["critical_violations"] == []
