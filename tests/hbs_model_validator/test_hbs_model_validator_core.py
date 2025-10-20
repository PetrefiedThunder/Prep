import json
from pathlib import Path

from hbs_model_validator.core import HBSModelValidator


def write_config(tmp_path: Path) -> Path:
    config = {
        "required_fields": ["id", "value"],
        "value_range": {"value": [0, 10]},
def _write_config(tmp_path):
    """Helper to create a simple schema configuration file."""
    config = {
        "schema": {"name": "string", "age": "int"},
        "required": ["name", "age"],
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
def test_load_config(tmp_path):
    validator = HBSModelValidator()
    config_path = _write_config(tmp_path)
    validator.load_config(str(config_path))

    assert validator.schema == {"name": "string", "age": "int"}
    assert validator.required_fields == ["name", "age"]


def test_validate_success(tmp_path):
    validator = HBSModelValidator()
    validator.load_config(str(_write_config(tmp_path)))

    model = {"name": "Alice", "age": 30}
    assert validator.validate(model) is True
    assert validator.errors == []
    assert "passed" in validator.generate_report().lower()


def test_validate_failure_and_report(tmp_path):
    validator = HBSModelValidator()
    validator.load_config(str(_write_config(tmp_path)))

    model = {"name": "Bob", "age": "thirty"}
    assert validator.validate(model) is False

    report = validator.generate_report().lower()
    assert "failed" in report
    assert "expected type int" in report
