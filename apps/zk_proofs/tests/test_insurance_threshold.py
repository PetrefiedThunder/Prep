"""Tests for the ZK insurance proof stubs."""
from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from apps.zk_proofs.main import app


client = TestClient(app)


def test_prove_and_verify_cycle() -> None:
    payload = base64.b64encode(b"policy").decode("utf-8")
    prove_resp = client.post("/zk/prove", params={"policy_pdf_b64": payload, "threshold": 1000000})
    proof_blob = prove_resp.json()["proof_blob"]
    verify_resp = client.post(
        "/zk/verify",
        json={"threshold": 1000000, "proof_blob": proof_blob},
    )
    assert verify_resp.json()["valid"] is True
