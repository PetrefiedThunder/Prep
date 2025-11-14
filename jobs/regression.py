"""Nightly regression suite verifying schema, API, and integration health."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi.testclient import TestClient

from prep.main import app
from prep.models import Kitchen
from prep.regulatory.apis.insurance import InsuranceVerificationAPI
from prep.reports.compliance import DEFAULT_REPORT_PATH, generate_compliance_manifest

LOGGER = logging.getLogger("prep.regression")


async def run_regression_suite() -> dict[str, bool]:
    """Execute regression checks and return a summary of pass/fail states."""

    results: dict[str, bool] = {}
    results["openapi"] = _verify_openapi_contract()
    results["metrics_endpoint"] = _verify_metrics_endpoint()
    results["model_schema"] = _verify_model_schema()
    results["insurance_integrations"] = _verify_insurance_integrations()
    results["manifest_generation"] = await _verify_manifest_generation()
    return results


def _verify_openapi_contract() -> bool:
    required_paths = {
        "/metrics",
        "/kitchens/{kitchen_id}/sanitation",
        "/kitchens/{kitchen_id}/compliance",
    }
    schema = app.openapi()
    available_paths = set(schema.get("paths", {}).keys())
    missing = required_paths - available_paths
    if missing:
        LOGGER.error("Missing OpenAPI paths: %s", ", ".join(sorted(missing)))
        return False
    return True


def _verify_metrics_endpoint() -> bool:
    client = TestClient(app)
    response = client.get("/metrics")
    if response.status_code != 200:
        LOGGER.error("/metrics endpoint returned %s", response.status_code)
        return False
    return b"prep_api_request_latency_seconds" in response.content


def _verify_model_schema() -> bool:
    expected_fields = {"delivery_only", "permit_types", "sanitation_logs"}
    missing = {field for field in expected_fields if not hasattr(Kitchen, field)}
    if missing:
        LOGGER.error("Kitchen model missing fields: %s", ", ".join(sorted(missing)))
        return False
    return True


def _verify_insurance_integrations() -> bool:
    api = InsuranceVerificationAPI()
    providers = set(api.providers.keys())
    required = {"next", "thimble"}
    if not required.issubset(providers):
        LOGGER.error(
            "Insurance providers missing integrations: %s", ", ".join(sorted(required - providers))
        )
        return False
    return True


async def _verify_manifest_generation() -> bool:
    try:
        path = await generate_compliance_manifest(DEFAULT_REPORT_PATH)
    except Exception as exc:  # pragma: no cover - diagnostics
        LOGGER.exception("Compliance manifest generation failed: %s", exc)
        return False
    return Path(path).exists()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    results = await run_regression_suite()
    failures: list[str] = [name for name, passed in results.items() if not passed]
    if failures:
        LOGGER.error("Regression suite failed checks: %s", ", ".join(failures))
        raise SystemExit(1)
    LOGGER.info("Regression suite completed successfully: %s", results)


if __name__ == "__main__":  # pragma: no cover - manual execution
    asyncio.run(main())
