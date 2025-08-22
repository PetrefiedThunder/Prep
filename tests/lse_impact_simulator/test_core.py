import json
import pytest

from lse_impact_simulator.core import LSEImpactSimulator


def _write_config(tmp_path, data, suffix=".json"):
    file = tmp_path / f"config{suffix}"
    if suffix in {".yaml", ".yml"}:
        yaml = pytest.importorskip("yaml")
        file.write_text(yaml.safe_dump(data))
    else:
        file.write_text(json.dumps(data))
    return file


def test_load_config_json(tmp_path):
    data = {"market": "LSE", "initial_price": 100.0, "volatility": 0.05}
    config_file = _write_config(tmp_path, data, ".json")
    sim = LSEImpactSimulator()
    sim.load_config(str(config_file))
    assert sim.config == data


def test_load_config_yaml(tmp_path):
    data = {"market": "LSE", "initial_price": 100.0, "volatility": 0.05}
    config_file = _write_config(tmp_path, data, ".yaml")
    sim = LSEImpactSimulator()
    sim.load_config(str(config_file))
    assert sim.config == data


def test_validate_success(tmp_path):
    data = {"market": "LSE", "initial_price": 100.0, "volatility": 0.05}
    config_file = _write_config(tmp_path, data)
    sim = LSEImpactSimulator()
    sim.load_config(str(config_file))
    assert sim.validate() is True


def test_validate_missing_field(tmp_path):
    data = {"initial_price": 100.0, "volatility": 0.05}
    config_file = _write_config(tmp_path, data)
    sim = LSEImpactSimulator()
    sim.load_config(str(config_file))
    with pytest.raises(ValueError):
        sim.validate()


def test_generate_report(tmp_path):
    data = {"market": "LSE", "initial_price": 100.0, "volatility": 0.05}
    config_file = _write_config(tmp_path, data)
    sim = LSEImpactSimulator()
    sim.load_config(str(config_file))
    report = sim.generate_report()
    assert "Market: LSE" in report
    assert "Initial Price: 100.0" in report
    assert "Volatility: 0.05" in report
    assert "Predicted Range:" in report
