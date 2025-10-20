import json
from pathlib import Path

import pytest

from lse_impact_simulator.core import LSEImpactSimulator

try:
    import yaml
except Exception:  # pragma: no cover - optional dependency
    yaml = None


def write_config(tmp_path: Path, data=None, suffix: str = ".json") -> Path:
    payload = data or {
        "market": "LSE",
        "initial_price": 100.0,
        "volatility": 0.05,
        "duration": 5,
    }
    path = tmp_path / f"config{suffix}"
    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            pytest.skip("PyYAML not available")
        path.write_text(yaml.safe_dump(payload))
    else:
        path.write_text(json.dumps(payload))
    return path


def test_load_config_json(tmp_path):
    path = write_config(tmp_path)
    sim = LSEImpactSimulator()
    sim.load_config(str(path))
    assert sim.config["market"] == "LSE"


def test_load_config_yaml(tmp_path):
    path = write_config(tmp_path, suffix=".yaml")
    sim = LSEImpactSimulator()
    sim.load_config(str(path))
    assert sim.config["duration"] == 5


def test_validate_success(tmp_path):
    path = write_config(tmp_path)
    sim = LSEImpactSimulator()
    sim.load_config(str(path))
    assert sim.validate() is True
    assert sim.validation_errors == []


def test_validate_missing_field(tmp_path):
    path = write_config(tmp_path, {"market": "LSE", "volatility": 0.05, "duration": 5})
    sim = LSEImpactSimulator()
    sim.load_config(str(path))
    assert sim.validate() is False
    assert "Invalid or missing config field: initial_price" in sim.generate_report()


def test_validate_negative_volatility(tmp_path):
    path = write_config(
        tmp_path,
        {"market": "LSE", "initial_price": 100, "volatility": -0.1, "duration": 5},
    )
    sim = LSEImpactSimulator()
    sim.load_config(str(path))
    assert sim.validate() is False
    assert "volatility must be non-negative" in sim.generate_report()


def test_generate_report(tmp_path):
    path = write_config(tmp_path)
    sim = LSEImpactSimulator()
    sim.load_config(str(path))
    report = sim.generate_report()
    assert "Market: LSE" in report
    assert "Predicted Range: ±5.0" in report
    assert "Projected Close: 105.0" in report


def test_generate_report_without_config():
    sim = LSEImpactSimulator()
    with pytest.raises(ValueError):
        sim.generate_report()
