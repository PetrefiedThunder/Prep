"""Requirement validation helpers for ETL jobs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

EXPECTED_PARTIES: tuple[str, ...] = (
    "kitchen_operator",
    "food_business",
    "marketplace_operator",
    "platform_developer",
)
VALID_SEVERITIES: set[str] = {"blocking", "conditional", "advisory"}


@dataclass(slots=True)
class RequirementValidationSummary:
    """Normalized result returned by :func:`validate_requirements`."""

    issues: list[str]
    counts_by_party: dict[str, int]
    blocking_count: int


class RequirementValidationError(ValueError):
    """Raised when requirement payloads fail validation."""

    def __init__(self, issues: Sequence[str]) -> None:
        joined = "\n - ".join(issues)
        message = f"Requirement validation failed:\n - {joined}" if issues else "Invalid requirements payload"
        super().__init__(message)
        self.issues = list(issues)


def _normalize_parties(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return [value.strip().lower()] if value.strip() else []
    if isinstance(value, Iterable):
        parties: list[str] = []
        for item in value:
            if not item:
                continue
            text = str(item).strip().lower()
            if text:
                parties.append(text)
        return parties
    return []


def _extract(field: str, requirement: Mapping[str, object]) -> object:
    if field in requirement:
        return requirement[field]
    metadata = requirement.get("metadata")
    if isinstance(metadata, Mapping) and field in metadata:
        return metadata[field]
    return None


def validate_requirements(
    requirements: Iterable[Mapping[str, object]],
    *,
    raise_on_error: bool = True,
    expected_parties: Iterable[str] = EXPECTED_PARTIES,
) -> RequirementValidationSummary:
    """Validate a collection of requirement payloads."""

    parties = [party.strip().lower() for party in expected_parties]
    counts = {party: 0 for party in parties}
    blocking_count = 0
    issues: list[str] = []

    reqs = list(requirements)
    if not reqs:
        issues.append("No requirements supplied for validation")

    for idx, requirement in enumerate(reqs, start=1):
        identifier = requirement.get("id") or requirement.get("requirement_id") or f"requirement #{idx}"
        applies_to = _normalize_parties(_extract("applies_to", requirement))
        if not applies_to:
            issues.append(f"{identifier}: missing applies_to audience tagging")
            continue

        severity_raw = _extract("severity", requirement)
        severity = str(severity_raw).strip().lower() if severity_raw else ""
        if not severity:
            issues.append(f"{identifier}: missing severity classification")
        elif severity not in VALID_SEVERITIES:
            issues.append(f"{identifier}: unsupported severity '{severity}'")
        if severity == "blocking":
            blocking_count += 1

        target_parties = applies_to
        if "all" in applies_to or "*" in applies_to:
            target_parties = parties

        for party in target_parties:
            if party not in counts:
                issues.append(f"{identifier}: references unknown party '{party}'")
                continue
            counts[party] += 1

    for party, count in counts.items():
        if count == 0:
            issues.append(f"No requirements tagged for party '{party}'")

    if blocking_count == 0:
        issues.append("At least one blocking severity requirement must be present")

    summary = RequirementValidationSummary(
        issues=list(issues),
        counts_by_party=counts,
        blocking_count=blocking_count,
    )

    if issues and raise_on_error:
        raise RequirementValidationError(issues)

    return summary
from __future__ import annotations
from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field
import sys, json

Party = Literal["kitchen_operator","food_business","marketplace_operator","platform_developer"]
Severity = Literal["blocking","conditional","advisory"]
class Requirement(BaseModel):
    id: str
    title: str
    applies_to: Party
    req_type: str
    authority: str
    citation: Optional[str] = None
    paperwork_ids: List[str] = Field(default_factory=list)
    fee_refs: List[str] = Field(default_factory=list)
    severity: Severity = "blocking"
class RequirementsBundle(BaseModel):
    jurisdiction: str
    version: str = "v1"
    requirements: List[Requirement] = Field(default_factory=list)
class RequirementsValidation(BaseModel):
    is_valid: bool
    issues: List[str]
    counts_by_party: Dict[Party, int]
    blocking_count: int
    has_fee_links: bool
def validate_requirements(bundle: RequirementsBundle, fee_names: List[str], paperwork_labels: List[str]) -> RequirementsValidation:
    issues: List[str] = []
    if not bundle.requirements: issues.append("No requirements listed.")
    seen = set(); blocking = 0
    counts: Dict[Party,int] = {p:0 for p in ["kitchen_operator","food_business","marketplace_operator","platform_developer"]}
    for r in bundle.requirements:
        if r.id in seen: issues.append(f"Duplicate requirement id: {r.id}")
        seen.add(r.id); counts[r.applies_to]+=1
        if r.severity == "blocking": blocking += 1
        if not r.title.strip(): issues.append(f"Empty title in {r.id}")
        if not r.authority.strip(): issues.append(f"Missing authority in {r.id}")
        for f in r.fee_refs:
            if f not in fee_names: issues.append(f"Unknown fee ref '{f}' in {r.id}")
        for p in r.paperwork_ids:
            if p not in paperwork_labels: issues.append(f"Unknown paperwork id '{p}' in {r.id}")
    return RequirementsValidation(
        is_valid=(len(issues)==0), issues=issues,
        counts_by_party=counts, blocking_count=blocking,
        has_fee_links=any(len(r.fee_refs)>0 for r in bundle.requirements)
    )
if __name__ == "__main__":
    # stdin expects:
    # {"bundle": {...}, "fee_names": ["Annual Permit"], "paperwork_labels": ["Application Form A-FOOD"]}
    payload = json.load(sys.stdin) if not sys.stdin.isatty() else {
        "bundle": {
            "jurisdiction":"san_francisco","version":"v1",
            "requirements":[
              {"id":"SFDPH-FOOD-PERMIT","title":"Food Facility Permit","applies_to":"food_business","req_type":"permit","authority":"SF DPH","fee_refs":["Annual Permit"],"paperwork_ids":["Application Form A-FOOD"],"severity":"blocking"}
            ]
        },
        "fee_names":["Annual Permit"],
        "paperwork_labels":["Application Form A-FOOD"]
    }
    b = RequirementsBundle(**payload["bundle"])
    res = validate_requirements(b, payload["fee_names"], payload["paperwork_labels"])
    print(res.model_dump_json(indent=2))
    sys.exit(0 if res.is_valid else 1)
