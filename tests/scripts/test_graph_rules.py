from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_graph_rules():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "graph_rules.py"
    spec = importlib.util.spec_from_file_location("graph_rules", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


graph_rules = load_graph_rules()


def test_sf_business_registration_branch():
    graph = graph_rules.build_sf_compliance_graph()
    assert "not payload.business_registration_certificate" in graph.nodes
    issue_label = "Issue: Business registration certificate is required"
    assert issue_label in graph.nodes
    assert (
        "not payload.business_registration_certificate",
        issue_label,
    ) in graph.edges


def test_health_permit_expiration_branch():
    graph = graph_rules.build_sf_compliance_graph()
    condition = "payload.health_permit_expires < today"
    status_label = 'status = "blocked"'
    assert condition in graph.nodes
    assert status_label in graph.nodes
    assert (condition, status_label) in graph.edges


def test_dot_output_contains_rankdir():
    graph = graph_rules.build_sf_compliance_graph()
    dot = graph.to_dot()
    assert "digraph SFCompliance" in dot
    assert "rankdir=LR" in dot
