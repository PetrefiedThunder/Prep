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
