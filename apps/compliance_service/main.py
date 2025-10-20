from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from prep.compliance.data_validator import DataValidator
from prep.compliance.food_safety_compliance_engine import (
    DataIntelligenceAPIClient,
    FoodSafetyComplianceEngine,
)


class KitchenPayload(BaseModel):
    """Typed payload used to validate kitchen requests."""

    model_config = ConfigDict(extra="allow")

    license_info: Dict[str, Any]
    inspection_history: list[Any] = Field(default_factory=list)


ENGINE_VERSION = FoodSafetyComplianceEngine.ENGINE_VERSION


def _build_engine() -> FoodSafetyComplianceEngine:
    """Instantiate the compliance engine with optional external client."""

    api_client: Optional[DataIntelligenceAPIClient] = None
    base_url = os.getenv("DATA_INTELLIGENCE_API_URL")
    if base_url:
        api_client = DataIntelligenceAPIClient(
            api_base_url=base_url,
            api_key=os.getenv("DATA_INTELLIGENCE_API_KEY", ""),
        )

    return FoodSafetyComplianceEngine(data_api_client=api_client)


engine = _build_engine()
app = FastAPI(title="Prep Compliance Service", version=ENGINE_VERSION)


@app.get("/healthz")
def health_check() -> Dict[str, Any]:
    """Simple readiness and liveness endpoint."""

    return {
        "status": "ok",
        "version": ENGINE_VERSION,
        "engine": engine.name,
    }


@app.post("/v1/report")
async def generate_compliance_report(payload: KitchenPayload) -> Dict[str, Any]:
    """Validate input payload and return a serialized compliance report."""

    kitchen_data = payload.model_dump()
    validation_errors = DataValidator.validate_kitchen_data(kitchen_data)
    if validation_errors:
        raise HTTPException(status_code=422, detail={"errors": validation_errors})

    try:
        report = engine.generate_report(kitchen_data)
    except Exception as exc:  # pragma: no cover - defensive logging
        raise HTTPException(
            status_code=500,
            detail={"error": "Engine execution failed", "details": str(exc)},
        ) from exc

    report_dict = asdict(report)
    report_dict["engine_version"] = engine.engine_version
    report_dict["rule_versions"] = engine.rule_versions
    return report_dict
