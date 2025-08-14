"""Tests for the ``prep.initialize`` function."""

import json

import prep

def test_initialize_with_path(tmp_path):
    """Configuration is loaded from an explicit path."""
    config = {"mode": "test"}
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(config))

    result = prep.initialize(cfg_file)
    assert result == config


def test_initialize_with_env_var(tmp_path, monkeypatch):
    """Configuration path is resolved via ``PREP_CONFIG`` env var."""
    config = {"mode": "env"}
    cfg_file = tmp_path / "env_config.json"
    cfg_file.write_text(json.dumps(config))
    monkeypatch.setenv("PREP_CONFIG", str(cfg_file))

    result = prep.initialize()
    assert result == config
