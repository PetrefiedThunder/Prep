"""Synthetic monitoring harness for regulatory endpoints.

This script issues HTTP requests against the city regulatory service
requirements and estimate endpoints and verifies that the p95 latency stays
below the configured threshold (200ms by default).

Usage::

    python perf/synthetics/run_synthetics.py --output perf/synthetics/out/latest.json

Configuration is controlled via environment variables so that CI pipelines or
cron jobs can point at staging or production clusters without modifying the
source tree::

``
SYNTHETIC_BASE_URL      Base URL for the regulatory service (required)
SYNTHETIC_JURISDICTIONS Comma-separated list of jurisdiction slugs to probe
                        (default: "san_francisco,joshua_tree")
SYNTHETIC_ITERATIONS    Number of samples per endpoint (default: 5)
SYNTHETIC_THRESHOLD_MS  Maximum allowable p95 latency in milliseconds (default: 200)
SYNTHETIC_IDEMPOTENCY   Optional idempotency key header value for estimate calls
```

The estimate endpoint payload can be customized per jurisdiction by providing a
JSON object via the ``--scenario`` flag. When omitted, the script will rely on
reasonable defaults baked into :data:`DEFAULT_SCENARIOS`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

DEFAULT_SCENARIOS: dict[str, dict[str, Any]] = {
    "san_francisco": {
        "seats": 24,
        "sqft": 1200,
        "inspections_per_year": 1,
        "reinspections_per_year": 0,
        "party": "food_business",
    },
    "joshua_tree": {
        "seats": 12,
        "sqft": 600,
        "inspections_per_year": 1,
        "reinspections_per_year": 0,
        "party": "kitchen_operator",
    },
}


@dataclass(slots=True)
class SampleResult:
    name: str
    method: str
    url: str
    durations_ms: list[float]
    status_codes: list[int]
    p95_ms: float
    threshold_ms: float
    passed: bool
    extra: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "method": self.method,
            "url": self.url,
            "durations_ms": self.durations_ms,
            "status_codes": self.status_codes,
            "p95_ms": self.p95_ms,
            "threshold_ms": self.threshold_ms,
            "passed": self.passed,
            "extra": self.extra,
        }


async def _sample_endpoint(
    client: httpx.AsyncClient,
    name: str,
    method: str,
    url: str,
    *,
    iterations: int,
    json_payload: dict[str, Any] | None,
    threshold_ms: float,
    headers: dict[str, str] | None = None,
) -> SampleResult:
    durations: list[float] = []
    status_codes: list[int] = []
    extra: dict[str, Any] = {"iterations": iterations}
    loop = asyncio.get_event_loop()
    for _ in range(iterations):
        start = loop.time()
        response = await client.request(method, url, json=json_payload, headers=headers)
        elapsed = (loop.time() - start) * 1000.0
        durations.append(elapsed)
        status_codes.append(response.status_code)
        response.raise_for_status()
    p95 = _percentile(durations, 95)
    return SampleResult(
        name=name,
        method=method,
        url=url,
        durations_ms=durations,
        status_codes=status_codes,
        p95_ms=p95,
        threshold_ms=threshold_ms,
        passed=p95 <= threshold_ms,
        extra=extra,
    )


def _percentile(samples: Iterable[float], percentile: float) -> float:
    """Return the percentile using the nearest-rank method."""

    ordered = sorted(samples)
    if not ordered:
        raise ValueError("Cannot compute percentile of an empty sample")
    k = max(1, int(round(percentile / 100.0 * len(ordered))))
    index = min(k - 1, len(ordered) - 1)
    return ordered[index]


async def run_synthetics(
    *,
    base_url: str,
    jurisdictions: Iterable[str],
    iterations: int,
    threshold_ms: float,
    scenario_overrides: dict[str, Any] | None,
    idempotency_key: str | None,
) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    scenarios = {**DEFAULT_SCENARIOS}
    if scenario_overrides:
        for slug, payload in scenario_overrides.items():
            scenarios[slug] = payload
    headers = {"User-Agent": "prep-synthetics/1.0"}
    estimate_headers = dict(headers)
    if idempotency_key:
        estimate_headers["Idempotency-Key"] = idempotency_key

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        results: list[SampleResult] = []
        for slug in jurisdictions:
            slug = slug.strip()
            if not slug:
                continue
            scenario = scenarios.get(slug)
            estimate_url = f"{base_url}/city/{slug}/requirements/estimate"
            requirements_url = f"{base_url}/city/{slug}/requirements"

            estimate_result = await _sample_endpoint(
                client,
                name=f"{slug}_estimate",
                method="POST",
                url=estimate_url,
                iterations=iterations,
                json_payload=scenario,
                threshold_ms=threshold_ms,
                headers=estimate_headers,
            )
            requirements_result = await _sample_endpoint(
                client,
                name=f"{slug}_requirements",
                method="GET",
                url=requirements_url,
                iterations=iterations,
                json_payload=None,
                threshold_ms=threshold_ms,
                headers=headers,
            )
            results.extend([estimate_result, requirements_result])

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "threshold_ms": threshold_ms,
        "iterations": iterations,
        "jurisdictions": [slug.strip() for slug in jurisdictions if slug.strip()],
        "checks": [result.to_json() for result in results],
    }
    summary["passed"] = all(result["passed"] for result in summary["checks"])
    summary["p95_by_check"] = {result["name"]: result["p95_ms"] for result in summary["checks"]}
    return summary


def _load_scenario_overrides(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise SystemExit(f"Invalid scenario override JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SystemExit("Scenario override payload must be an object keyed by jurisdiction slug")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run synthetic monitoring probes")
    parser.add_argument(
        "--output",
        type=Path,
        help="Where to write the JSON summary (optional).",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=os.environ.get("SYNTHETIC_SCENARIOS"),
        help="JSON blob with jurisdiction -> payload overrides",
    )
    args = parser.parse_args()

    base_url = os.environ.get("SYNTHETIC_BASE_URL")
    if not base_url:
        raise SystemExit("SYNTHETIC_BASE_URL is required")

    jurisdictions = os.environ.get("SYNTHETIC_JURISDICTIONS", "san_francisco,joshua_tree").split(
        ","
    )
    iterations = int(os.environ.get("SYNTHETIC_ITERATIONS", "5"))
    threshold_ms = float(os.environ.get("SYNTHETIC_THRESHOLD_MS", "200"))
    idempotency_key = os.environ.get("SYNTHETIC_IDEMPOTENCY")

    scenario_overrides = _load_scenario_overrides(args.scenario)

    summary = asyncio.run(
        run_synthetics(
            base_url=base_url,
            jurisdictions=jurisdictions,
            iterations=iterations,
            threshold_ms=threshold_ms,
            scenario_overrides=scenario_overrides,
            idempotency_key=idempotency_key,
        )
    )

    output = json.dumps(summary, indent=2, sort_keys=True)
    print(output)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
