#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import traceback

# Ensure package imports resolve when executed as a script
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        kitchen_data_json = sys.argv[1]
    else:
        try:
            kitchen_data_json = sys.stdin.read()
        except Exception as exc:  # pragma: no cover - defensive guard
            output = {
                "error": "Failed to read input from stdin",
                "details": str(exc),
                "status": "error",
                "traceback": traceback.format_exc(),
            }
            print(json.dumps(output))
            return 1

        if not kitchen_data_json.strip():
            output = {
                "error": "No kitchen data provided",
                "usage": "python run_compliance_check.py '<kitchen_data_json>'",
                "status": "error",
            }
            print(json.dumps(output))
            return 1
    try:
        kitchen_data = json.loads(kitchen_data_json)
    except json.JSONDecodeError as exc:
        output = {
            "error": "Invalid JSON input",
            "details": str(exc),
            "status": "error",
            "traceback": traceback.format_exc(),
        }
        print(json.dumps(output))
        return 1

    try:
        try:
            from .food_safety_compliance_engine import (
                DataIntelligenceAPIClient,
                FoodSafetyComplianceEngine,
            )
        except ImportError:
            from food_safety_compliance_engine import (  # type: ignore
                DataIntelligenceAPIClient,
                FoodSafetyComplianceEngine,
            )
    except Exception as exc:
        output = {
            "error": "Could not import compliance engine",
            "details": str(exc),
            "status": "error",
            "traceback": traceback.format_exc(),
        }
        print(json.dumps(output))
        return 1

    data_api_client = None
    api_url = os.getenv("DATA_INTELLIGENCE_API_URL")
    api_key = os.getenv("DATA_INTELLIGENCE_API_KEY")
    if api_url and api_key:
        try:
            data_api_client = DataIntelligenceAPIClient(api_url, api_key)
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "warning": "Could not initialize Data Intelligence API client",
                        "details": str(exc),
                    }
                ),
                file=sys.stderr,
            )

    strict_mode_env = os.getenv("FOOD_SAFETY_STRICT_MODE")
    if strict_mode_env is not None:
        strict_mode = strict_mode_env.lower() in {"1", "true", "yes", "on"}
    else:
        strict_mode = os.getenv("ENVIRONMENT", "").lower() == "production"

    try:
        engine = FoodSafetyComplianceEngine(
            data_api_client=data_api_client,
            strict_mode=strict_mode,
        )
    except Exception as exc:
        output = {
            "error": "Failed to initialize compliance engine",
            "details": str(exc),
            "traceback": traceback.format_exc(),
            "status": "error",
        }
        print(json.dumps(output))
        return 1

    try:
        report = engine.generate_report(kitchen_data)
    except Exception as exc:
        output = {
            "error": "Compliance check failed during execution",
            "details": str(exc),
            "traceback": traceback.format_exc(),
            "type": exc.__class__.__name__,
            "status": "error",
        }
        print(json.dumps(output))
        return 1

    violations_payload = [
        {
            "rule_id": violation.rule_id,
            "rule_name": violation.rule_name,
            "message": violation.message,
            "severity": violation.severity,
            "context": violation.context,
            "timestamp": violation.timestamp.isoformat(),
            "rule_version": violation.rule_version,
            "evidence_path": violation.evidence_path,
            "observed_value": violation.observed_value,
        }
        for violation in report.violations_found
    ]

    critical_violations = [
        violation for violation in report.violations_found if violation.severity == "critical"
    ]
    critical_payload = [
        {
            "rule_id": violation.rule_id,
            "rule_name": violation.rule_name,
            "message": violation.message,
            "severity": violation.severity,
            "context": violation.context,
            "timestamp": violation.timestamp.isoformat(),
            "rule_version": violation.rule_version,
            "evidence_path": violation.evidence_path,
            "observed_value": violation.observed_value,
        }
        for violation in critical_violations
    ]

    can_accept = len(critical_violations) == 0

    try:
        badge = engine.generate_kitchen_safety_badge(kitchen_data, report=report)
    except Exception as exc:
        output = {
            "error": "Safety badge generation failed",
            "details": str(exc),
            "traceback": traceback.format_exc(),
            "status": "error",
        }
        print(json.dumps(output))
        return 1

    report_dict = {
        "engine_name": report.engine_name,
        "timestamp": report.timestamp.isoformat(),
        "overall_compliance_score": report.overall_compliance_score,
        "total_rules_checked": report.total_rules_checked,
        "summary": report.summary,
        "recommendations": report.recommendations,
        "violations_found": violations_payload,
        "passed_rules": report.passed_rules,
        "engine_version": report.engine_version,
        "rule_versions": report.rule_versions,
    }
    if report.report_signature is not None:
        report_dict["report_signature"] = report.report_signature

    output = {
        **report_dict,
        "can_accept_bookings": can_accept,
        "critical_violations": critical_payload,
        "safety_badge": badge,
        "detailed_analysis": {
            "licensing_issues": len(
                [v for v in report.violations_found if "license" in v.rule_id.lower()]
            ),
            "inspection_issues": len(
                [v for v in report.violations_found if "inspect" in v.rule_id.lower()]
            ),
            "certification_issues": len(
                [v for v in report.violations_found if "cert" in v.rule_id.lower()]
            ),
            "equipment_issues": len(
                [v for v in report.violations_found if "equip" in v.rule_id.lower()]
            ),
            "marketplace_issues": len(
                [v for v in report.violations_found if "prep" in v.rule_id.lower()]
            ),
            "operational_issues": len(
                [v for v in report.violations_found if "ops" in v.rule_id.lower()]
            ),
        },
        "raw_report": {
            **report_dict,
            "can_accept_bookings": can_accept,
            "critical_violations": critical_payload,
            "safety_badge": badge,
        },
        "status": "success",
    }

    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
