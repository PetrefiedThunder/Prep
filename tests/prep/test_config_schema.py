"""Tests for the shared configuration schema helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

import prep.utility.config_schema as config_schema
from prep.utility.config_schema import BaseConfigSchema, IterableValidationMixin


class ExampleSchema(BaseConfigSchema):
    """Concrete schema used for exercising the base helpers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._required_keys = {"name"}

    def _normalise_config(self, config: dict[str, Any]) -> dict[str, Any]:
        # Normalise the keys so the behaviour can be asserted in tests.
        return {key.lower(): value for key, value in config.items()}

    def _run_validation(self, *args: Any, **kwargs: Any) -> list[str]:
        errors = []
        for key in sorted(self._required_keys):
            if key not in self.config:
                errors.append(f"Missing required key: {key}")
        return errors


class OptionalSchema(ExampleSchema):
    def __init__(self) -> None:
        super().__init__(config_required=False)


class DummyIterableSchema(IterableValidationMixin):
    def _ensure(self, values: Iterable[Any]) -> list[Any]:
        return self._ensure_list(values)


@pytest.fixture()
def config_file(tmp_path: Path) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"NAME": "Prep"}), encoding="utf-8")
    return path


def test_load_config_reads_json_and_resets_state(config_file: Path) -> None:
    schema = ExampleSchema()
    loaded = schema.load_config(str(config_file))

    assert loaded == {"name": "Prep"}
    assert schema.config == {"name": "Prep"}
    assert schema.validation_errors == []
    assert schema._validated is False  # type: ignore[attr-defined]


def test_load_config_requires_mapping(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    schema = ExampleSchema()
    with pytest.raises(TypeError):
        schema.load_config(str(config_path))


def test_validate_reports_success(config_file: Path, caplog: pytest.LogCaptureFixture) -> None:
    schema = ExampleSchema()
    schema.load_config(str(config_file))

    with caplog.at_level("INFO"):
        assert schema.validate() is True

    assert schema.validation_errors == []
    assert schema.generate_report() == "Validation passed."


def test_generate_report_requires_validate(config_file: Path) -> None:
    schema = ExampleSchema()
    schema.load_config(str(config_file))

    with pytest.raises(ValueError):
        schema.generate_report()


def test_validate_collects_errors(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"OTHER": "value"}), encoding="utf-8")

    schema = ExampleSchema()
    schema.load_config(str(config_path))

    with caplog.at_level("WARNING"):
        assert schema.validate() is False

    assert schema.validation_errors == ["Missing required key: name"]
    report = schema.generate_report()
    assert "Validation failed." in report
    assert "- Missing required key: name" in report


def test_ensure_config_loaded_respects_optional_schema() -> None:
    schema = OptionalSchema()
    assert schema.ensure_config_loaded() == {}


def test_ensure_config_loaded_raises_when_required() -> None:
    schema = ExampleSchema()
    with pytest.raises(ValueError, match="Configuration not loaded"):
        schema.ensure_config_loaded()


def test_yaml_requires_dependency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    schema = ExampleSchema()
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text("name: Prep", encoding="utf-8")

    monkeypatch.setattr(config_schema, "yaml", None, raising=False)

    with pytest.raises(ImportError):
        schema.load_config(str(yaml_path))


def test_yaml_uses_safe_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text("name: Prep", encoding="utf-8")

    class DummyYAML:
        @staticmethod
        def safe_load(handle: Any) -> dict[str, Any]:
            return {"name": handle.read().split(":", 1)[1].strip()}

    monkeypatch.setattr(config_schema, "yaml", DummyYAML(), raising=False)

    schema = ExampleSchema()
    assert schema.load_config(str(yaml_path)) == {"name": "Prep"}


def test_iterable_validation_mixin_converts_iterables() -> None:
    helper = DummyIterableSchema()

    result = helper._ensure(values={"a", "b"})
    assert isinstance(result, list)
    assert sorted(result) == ["a", "b"]

    same_list = [1, 2, 3]
    assert helper._ensure(values=same_list) is same_list
