"""FastAPI endpoints exposing regulatory requirement bundles per city."""

from __future__ import annotations

import json
import logging
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from prep.data_pipeline.cdc import (
    BigQueryDestination,
    CDCStreamManager,
    SchemaRegistry,
    SnowflakeDestination,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/city", tags=["city-requirements"])


class RequirementEntry(BaseModel):
    """Single regulatory obligation in the requirements bundle."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str = Field(..., description="Canonical identifier for the obligation")
    title: str = Field(..., description="Display title for the obligation")
    applies_to: str = Field(..., description="Party responsible for fulfilling the obligation")
    req_type: str = Field(..., alias="requirement_type", description="Requirement category")
    authority: str = Field(..., description="Issuing authority")
    severity: str = Field(..., description="Severity level (blocking, conditional, advisory)")
    rationale: str = Field(..., description="Short explanation for why the obligation matters")
    fee_links: list[str] = Field(
        default_factory=list,
        description="Optional list of URLs pointing to fee schedules or calculators",
    )
    documents: list[str] = Field(
        default_factory=list,
        description="Supporting documents typically requested during submission",
    )


class ChangeCandidate(BaseModel):
    """Potential policy change under consideration for the jurisdiction."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    title: str
    action: str
    impact: str
    rationale: str = Field(
        ..., description="Narrative explaining the expected outcome of the change"
    )


class ValidationSummary(BaseModel):
    """Validation metadata returned alongside the requirements bundle."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    is_valid: bool = Field(..., description="Whether the bundle passes structural validation")
    issues: list[str] = Field(default_factory=list, description="Validation warnings")
    counts_by_party: dict[str, int] = Field(
        default_factory=dict,
        description="Requirement counts grouped by responsible party",
    )
    blocking_count: int = Field(0, description="Number of obligations marked as blocking")
    has_fee_links: bool = Field(
        False, description="True when any requirement links to a fee schedule"
    )
    change_candidate_count: int = Field(
        0, description="Number of change candidates tracked for the jurisdiction"
    )


class RequirementsBundleResponse(BaseModel):
    """Response payload returned by the requirements endpoint."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    jurisdiction: str
    version: str = Field(default="v1")
    status: str = Field(..., description="Readiness status derived from blocking requirements")
    requirements: list[RequirementEntry] = Field(default_factory=list)
    change_candidates: list[ChangeCandidate] = Field(default_factory=list)
    validation: ValidationSummary
    rationales: dict[str, str] = Field(
        default_factory=dict,
        description="Narratives keyed by responsible party for UI display",
    )


_DATA_PATH = Path(__file__).resolve().parents[2] / "policy" / "rego" / "city" / "data.json"

_POLICY_DECISION_SCHEMA: dict[str, Any] = {
    "jurisdiction": "string",
    "version": "string",
    "status": "string",
    "counts_by_party": "object",
    "blocking_count": "integer",
    "change_candidate_count": "integer",
}

_EVENT_STREAM = CDCStreamManager(
    registry=SchemaRegistry(),
    bigquery=BigQueryDestination(project_id="prep-sandbox", dataset="policy_decisions"),
    snowflake=SnowflakeDestination(account=None, database=None, schema=None),
)

_LAST_STATUS: dict[str, str] = {}


def get_policy_event_stream() -> CDCStreamManager:
    """Expose the event stream for test instrumentation."""

    return _EVENT_STREAM


@lru_cache
def _load_raw_data() -> dict[str, Any]:
    """Load the static policy data backing the endpoint."""

    if not _DATA_PATH.exists():
        raise FileNotFoundError(f"Missing policy data file at {_DATA_PATH}")
    with _DATA_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    data = payload.get("city", {}).get("requirements", {})
    if not isinstance(data, dict):
        raise ValueError("Policy data format is invalid: expected mapping")
    return data


def _normalize_city(city: str) -> str:
    """Return the canonical slug for a city identifier."""

    return "_".join(part for part in city.strip().lower().replace("-", " ").split())


def _build_validation(
    requirements: list[RequirementEntry],
    change_candidates: list[ChangeCandidate],
    rationales: dict[str, str],
) -> ValidationSummary:
    """Construct the validation payload for the bundle."""

    counts = Counter(req.applies_to for req in requirements)
    blocking_count = sum(1 for req in requirements if req.severity.lower() == "blocking")
    has_fee_links = any(bool(req.fee_links) for req in requirements)
    for party in rationales:
        counts.setdefault(party, 0)
    counts["change_candidates"] = len(change_candidates)
    is_valid = bool(requirements)
    issues: list[str] = [] if is_valid else ["No requirements configured for jurisdiction"]
    return ValidationSummary(
        is_valid=is_valid,
        issues=issues,
        counts_by_party=dict(sorted(counts.items())),
        blocking_count=blocking_count,
        has_fee_links=has_fee_links,
        change_candidate_count=len(change_candidates),
    )


def _hydrate_bundle(city: str, payload: dict[str, Any]) -> RequirementsBundleResponse:
    """Convert raw JSON payloads into the structured response model."""

    requirements = [
        RequirementEntry.model_validate(item) for item in payload.get("requirements", [])
    ]
    change_candidates = [
        ChangeCandidate.model_validate(item) for item in payload.get("change_candidates", [])
    ]
    rationales = {str(key): str(value) for key, value in (payload.get("rationales") or {}).items()}
    validation = _build_validation(requirements, change_candidates, rationales)
    status = "ready" if validation.blocking_count == 0 else "attention_required"
    version = str(payload.get("version", "v1"))
    return RequirementsBundleResponse(
        jurisdiction=city,
        version=version,
        status=status,
        requirements=requirements,
        change_candidates=change_candidates,
        validation=validation,
        rationales=rationales,
    )


async def _emit_policy_decision(bundle: RequirementsBundleResponse) -> None:
    """Send a policy.decision event describing the bundle state."""

    payload = {
        "jurisdiction": bundle.jurisdiction,
        "version": bundle.version,
        "status": bundle.status,
        "counts_by_party": bundle.validation.counts_by_party,
        "blocking_count": bundle.validation.blocking_count,
        "change_candidate_count": bundle.validation.change_candidate_count,
    }
    await _EVENT_STREAM.publish("policy.decision", payload, _POLICY_DECISION_SCHEMA)
    logger.info(
        "Emitted policy.decision",
        extra={"jurisdiction": bundle.jurisdiction, "status": bundle.status},
    )


def _get_bundle(city: str) -> RequirementsBundleResponse:
    raw_data = _load_raw_data()
    payload = raw_data.get(city)
    if payload is None:
        raise KeyError(city)
    return _hydrate_bundle(city, payload)


@router.get("/{city}/requirements", response_model=RequirementsBundleResponse)
async def get_city_requirements(city: str) -> RequirementsBundleResponse:
    """Return the requirements bundle for the specified city."""

    slug = _normalize_city(city)
    try:
        bundle = _get_bundle(slug)
    except KeyError as exc:  # pragma: no cover - FastAPI surfaces as 404
        raise HTTPException(status_code=404, detail=f"Unsupported city '{city}'") from exc
    previous_status = _LAST_STATUS.get(slug)
    if previous_status != bundle.status:
        await _emit_policy_decision(bundle)
        _LAST_STATUS[slug] = bundle.status
    return bundle
