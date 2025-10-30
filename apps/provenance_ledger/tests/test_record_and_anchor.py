"""Tests for provenance ledger operations."""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.provenance_ledger.anchor import anchor_to_chain, build_daily_merkle_root
from apps.provenance_ledger.main import app


client = TestClient(app)


def test_record_creates_hash() -> None:
    payload = {"type": "document", "parent_hash": None, "payload": {"value": 1}}
    response = client.post("/prov/record", json=payload)
    data = response.json()
    assert "hash" in data


def test_anchor_roundtrip() -> None:
    root = build_daily_merkle_root()
    txid = anchor_to_chain(root)
    assert isinstance(txid, str)
    assert txid
