from __future__ import annotations
import os, uuid, time, requests
from typing import Dict, Any
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181")
def evaluate(package_path: str, opa_input: Dict[str, Any]) -> Dict[str, Any]:
    t0 = time.perf_counter_ns()
    r = requests.post(f"{OPA_URL}/v1/data/{package_path}", json={"input": opa_input}, timeout=3)
    r.raise_for_status()
    allow = bool(r.json().get("result", False))
    rationale = opa_input.get("requirement_id") or "n/a"
    return {
        "decision_id": str(uuid.uuid4()),
        "allow": allow,
        "rationale": rationale,
        "latency_ms": int((time.perf_counter_ns() - t0) / 1_000_000),
    }
