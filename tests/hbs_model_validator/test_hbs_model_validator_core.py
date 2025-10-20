import json

from hbs_model_validator.core import HBSModelValidator


def _write_config(tmp_path):
    """Helper to create a simple schema configuration file."""
    config = {
        "schema": {"name": "string", "age": "int"},
        "required": ["name", "age"],
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    return path


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
