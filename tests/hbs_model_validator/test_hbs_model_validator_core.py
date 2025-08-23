import json
from pathlib import Path

from hbs_model_validator.core import HBSModelValidator


def write_config(tmp_path: Path) -> Path:
    config = {
        "required_fields": ["id", "value"],
        "value_range": {"value": [0, 10]},
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    return path


def test_load_config(tmp_path: Path) -> None:
    validator = HBSModelValidator()
    config_path = write_config(tmp_path)
    validator.load_config(str(config_path))
    assert validator.config == {
        "required_fields": ["id", "value"],
        "value_range": {"value": [0, 10]},
    }


def test_validate_success_and_report(tmp_path: Path) -> None:
    validator = HBSModelValidator()
    config_path = write_config(tmp_path)
    validator.load_config(str(config_path))
    model = {"id": 1, "value": 5}
    assert validator.validate(model) is True
    report = validator.generate_report()
    assert "passed" in report
    assert "Errors" not in report


def test_validate_failure_and_report(tmp_path: Path) -> None:
    validator = HBSModelValidator()
    config_path = write_config(tmp_path)
    validator.load_config(str(config_path))
    model = {"id": 1, "value": 50}
    assert validator.validate(model) is False
    report = validator.generate_report()
    assert "failed" in report
    assert "out of range" in report
