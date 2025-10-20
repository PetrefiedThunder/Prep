import json
from pathlib import Path

import pytest

from hbs_model_validator.core import HBSModelValidator


def write_config(tmp_path: Path) -> Path:
    config = {
        "required_fields": ["id", "value"],
        "value_range": {"value": [0, 10]},
        "schema": {"label": "string"},
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    return path


def test_load_config(tmp_path: Path) -> None:
    validator = HBSModelValidator()
    config_path = write_config(tmp_path)
    validator.load_config(str(config_path))
    assert validator.config["required_fields"] == ["id", "value"]
    assert validator.config["value_range"] == {"value": [0.0, 10.0]}


def test_validate_success_and_report(tmp_path: Path) -> None:
    validator = HBSModelValidator()
    validator.load_config(str(write_config(tmp_path)))
    model = {"id": 1, "value": 5, "label": "ok"}
    assert validator.validate(model) is True
    report = validator.generate_report()
    assert "passed" in report
    assert "Errors" not in report


def test_validate_failure_and_report(tmp_path: Path) -> None:
    validator = HBSModelValidator()
    validator.load_config(str(write_config(tmp_path)))
    model = {"id": 1, "value": 50, "label": 10}
    assert validator.validate(model) is False
    report = validator.generate_report()
    assert "failed" in report
    assert "out of range" in report
    assert "expected type string" in report


def test_generate_report_without_validation(tmp_path: Path) -> None:
    validator = HBSModelValidator()
    validator.load_config(str(write_config(tmp_path)))
    with pytest.raises(ValueError):
        validator.generate_report()


def test_load_config_invalid_schema(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"schema": {"name": "unknown"}}))
    validator = HBSModelValidator()
    with pytest.raises(ValueError):
        validator.load_config(str(config_path))
