"""Tests for the ``prep.initialize`` function."""

import json
import importlib

import pytest
import prep


@pytest.fixture
def fresh_prep():
    """Reload the :mod:`prep` module to reset cached configuration."""
    importlib.reload(prep)
    return prep


def test_initialize_with_path(tmp_path, fresh_prep):
    """Configuration is loaded from an explicit path."""
    config = {"mode": "test"}
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(config))
    result = fresh_prep.initialize(cfg_file)
    assert result == config


def test_initialize_with_env_var(tmp_path, monkeypatch, fresh_prep):
    """Configuration path is resolved via ``PREP_CONFIG`` env var."""
    config = {"mode": "env"}
    cfg_file = tmp_path / "env_config.json"
    cfg_file.write_text(json.dumps(config))
    monkeypatch.setenv("PREP_CONFIG", str(cfg_file))
    result = fresh_prep.initialize()
    assert result == config


def test_initialize_caches(tmp_path, fresh_prep):
    """Repeated calls without path reuse cached data."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"a": 1}))
    first = fresh_prep.initialize(cfg_file)
    cfg_file.write_text(json.dumps({"a": 2}))
    second = fresh_prep.initialize()
    assert first == {"a": 1}
    assert second == {"a": 1}
