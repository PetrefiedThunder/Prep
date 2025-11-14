"""Configuration helpers for the Codex service."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

_ENV_FILE_ENV = "CODEX_ENV_FILE"
_DEFAULT_ENV_FILE = Path(".env.codex")


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse a simple ``KEY=VALUE`` style environment file."""

    if not path.exists() or not path.is_file():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


class Settings(BaseModel):
    """Runtime configuration for the Codex backend."""

    environment: str = Field(default="development", alias="CODEX_ENVIRONMENT")
    database_url: str = Field(default="sqlite+aiosqlite:///./codex.db", alias="CODEX_DATABASE_URL")
    database_pool_size: int = Field(default=10, ge=1, alias="CODEX_DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, ge=0, alias="CODEX_DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, ge=1, alias="CODEX_DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=1800, ge=1, alias="CODEX_DATABASE_POOL_RECYCLE")
    database_echo: bool = Field(default=False, alias="CODEX_DATABASE_ECHO")

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        allowed = {"development", "staging", "production"}
        normalized = value.lower()
        if normalized not in allowed:
            raise ValueError(f"CODEX_ENVIRONMENT must be one of {sorted(allowed)}")
        return normalized

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        if not value:
            raise ValueError("CODEX_DATABASE_URL must not be empty")
        if "://" not in value:
            raise ValueError("CODEX_DATABASE_URL must be a valid database URL")
        return value

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


def _collect_environment(env_file: Path | None) -> dict[str, Any]:
    env: dict[str, Any] = {}
    env.update(_parse_env_file(env_file or _DEFAULT_ENV_FILE))
    env.update(os.environ)
    return env


def load_settings(*, env_file: Path | None = None, env: dict[str, Any] | None = None) -> Settings:
    """Load configuration from environment variables."""

    raw_env = _collect_environment(env_file)
    if env:
        raw_env.update(env)
    try:
        return Settings.model_validate(raw_env)
    except ValidationError as exc:  # pragma: no cover - configuration errors
        message = ", ".join(err["msg"] for err in exc.errors())
        raise RuntimeError(f"Invalid Codex configuration: {message}") from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""

    env_path = os.getenv(_ENV_FILE_ENV)
    path = Path(env_path) if env_path else _DEFAULT_ENV_FILE
    return load_settings(env_file=path)


def reset_settings_cache() -> None:
    """Reset the cached settings instance (primarily for tests)."""

    get_settings.cache_clear()


__all__ = [
    "Settings",
    "get_settings",
    "load_settings",
    "reset_settings_cache",
]
