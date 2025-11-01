from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "audit_config_parity.py"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "regengine" / "cities" / "san_francisco" / "config.yaml"
DEFAULT_SERVICES = REPO_ROOT / "apps" / "sf_regulatory_service" / "services.py"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.mark.skipif(not SCRIPT_PATH.exists(), reason="audit script missing")
def test_audit_passes_for_current_configuration(tmp_path: Path) -> None:
    output_path = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--config",
            str(DEFAULT_CONFIG),
            "--services",
            str(DEFAULT_SERVICES),
            "--output",
            str(output_path),
            "--fail-on-issues",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["status"] == "pass"
    assert data["unused_config_keys"] == []
    assert data["missing_validators"] == []


@pytest.mark.skipif(not SCRIPT_PATH.exists(), reason="audit script missing")
def test_audit_flags_unused_and_missing_keys(tmp_path: Path) -> None:
    output_path = tmp_path / "report.json"
    config_path = FIXTURE_DIR / "gapped_config.yaml"
    services_path = FIXTURE_DIR / "gapped_services.py"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--config",
            str(config_path),
            "--services",
            str(services_path),
            "--output",
            str(output_path),
            "--fail-on-issues",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["status"] == "fail"
    assert data["unused_config_keys"] == ["health_permit", "noise"]
    assert data["missing_validators"] == ["fire"]
