"""Utilities for aggregating San Francisco audit results."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Mapping


DOMAIN_LABELS: Mapping[str, str] = {
    "test_business_registration_controls": "business_registration",
    "test_health_permit_controls": "health_permits",
    "test_fire_and_waste_controls": "fire_and_waste",
    "test_zoning_audit_controls": "zoning",
    "test_tax_compliance_controls": "tax",
    "test_observability_and_metrics": "observability",
    "test_security_and_slack_reporting": "security_and_reporting",
}


@dataclass(frozen=True)
class DomainStatus:
    """Summary for a compliance domain."""

    name: str
    passed: bool
    failed_tests: tuple[str, ...]


def load_pytest_report(path: Path) -> dict[str, object]:
    """Return the parsed pytest-json-report payload."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):  # pragma: no cover - defensive guard
        raise ValueError("pytest JSON report must decode to a dictionary")
    return data


def _extract_tests(report: Mapping[str, object]) -> Iterable[Mapping[str, object]]:
    tests = report.get("tests")
    if isinstance(tests, list):
        for entry in tests:
            if isinstance(entry, Mapping):
                yield entry


def summarize_domains(report: Mapping[str, object]) -> list[DomainStatus]:
    """Collapse individual pytest cases into compliance domain results."""

    failures: dict[str, list[str]] = defaultdict(list)
    outcomes: dict[str, list[str]] = defaultdict(list)

    for test in _extract_tests(report):
        nodeid = str(test.get("nodeid", ""))
        case = nodeid.split("::")[-1]
        domain = DOMAIN_LABELS.get(case)
        if domain is None:
            continue
        outcome = str(test.get("outcome", "unknown"))
        outcomes[domain].append(outcome)
        if outcome not in {"passed", "skipped"}:
            failures[domain].append(case)

    summaries: list[DomainStatus] = []
    for case_name, domain in DOMAIN_LABELS.items():
        domain_outcomes = outcomes.get(domain, [])
        passed = bool(domain_outcomes) and all(outcome == "passed" for outcome in domain_outcomes)
        summaries.append(
            DomainStatus(
                name=domain,
                passed=passed,
                failed_tests=tuple(sorted(failures.get(domain, ()))),
            )
        )
    return summaries


def build_audit_report(report: Mapping[str, object]) -> dict[str, object]:
    """Render a condensed audit report suitable for Slack and S3 publishing."""

    domains = summarize_domains(report)
    summary_counts = report.get("summary", {})
    created = report.get("created")
    if isinstance(created, str):
        generated_at = created
    else:
        generated_at = datetime.now(tz=UTC).isoformat()

    return {
        "generated_at": generated_at,
        "summary": {
            "passed": int(summary_counts.get("passed", 0) or 0),
            "failed": int(summary_counts.get("failed", 0) or 0),
            "total": int(summary_counts.get("total", 0) or 0),
        },
        "domains": [
            {
                "name": domain.name,
                "status": "passed" if domain.passed else "failed",
                "failing_tests": list(domain.failed_tests),
            }
            for domain in domains
        ],
    }


def build_slack_payload(audit_report: Mapping[str, object]) -> dict[str, object]:
    """Return a Slack payload summarising audit results."""

    domains = audit_report.get("domains", [])
    lines: list[str] = []
    for entry in domains:
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name", "unknown"))
        status = str(entry.get("status", "unknown"))
        icon = "✅" if status == "passed" else "❌"
        lines.append(f"{icon} *{name.replace('_', ' ').title()}* — {status}")

    text = "SF Regulatory Audit Results\n" + "\n".join(lines)
    return {
        "text": text,
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            }
        ],
    }


def write_audit_report(report: Mapping[str, object], output_path: Path) -> None:
    """Serialize the audit report as JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


__all__ = [
    "DOMAIN_LABELS",
    "DomainStatus",
    "load_pytest_report",
    "summarize_domains",
    "build_audit_report",
    "build_slack_payload",
    "write_audit_report",
]
