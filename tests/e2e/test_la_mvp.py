"""End-to-end scaffolding test for LA MVP."""
from __future__ import annotations

import importlib


SERVICE_MODULES = [
    "apps.ingestion_service.main",
    "apps.graph_service.main",
    "apps.obligation_extractor.main",
    "apps.formalizer.catala",
    "apps.policy_engine.main",
    "apps.provenance_ledger.main",
    "apps.zk_proofs.main",
    "apps.monitor.main",
    "apps.predictor.main",
    "apps.twin.main",
]


def test_services_importable() -> None:
    for module_name in SERVICE_MODULES:
        module = importlib.import_module(module_name)
        assert module is not None
