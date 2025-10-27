"""Environment-aware configuration for the Prep platform."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from pydantic import AnyUrl, BaseModel, Field, ValidationError, field_validator
from pydantic import PostgresDsn

_ENV_FILE_ENV = "PREP_ENV_FILE"
_DEFAULT_ENV_FILE = Path(".env")


def _parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a simple ``.env`` file into a dictionary."""

    values: Dict[str, str] = {}
    if not path.exists() or not path.is_file():
        return values

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


class Settings(BaseModel):
    """Strongly typed runtime configuration."""

    environment: str = Field(default="development", alias="ENVIRONMENT")
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://prep:prep@localhost:5432/prep", alias="DATABASE_URL"
    )
    redis_url: AnyUrl = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    database_pool_size: int = Field(default=10, ge=1, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, ge=0, alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, ge=1, alias="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=1800, ge=1, alias="DATABASE_POOL_RECYCLE")
    session_ttl_seconds: int = Field(default=3600, ge=300, alias="SESSION_TTL_SECONDS")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60, ge=5, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    stripe_secret_key: str | None = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_connect_refresh_url: AnyUrl = Field(
        default="https://example.com/stripe/refresh", alias="STRIPE_CONNECT_REFRESH_URL"
    )
    stripe_connect_return_url: AnyUrl = Field(
        default="https://example.com/stripe/return", alias="STRIPE_CONNECT_RETURN_URL"
    )
    stripe_api_key: str | None = Field(default=None, alias="STRIPE_API_KEY")
    stripe_currency: str = Field(default="usd", alias="STRIPE_CURRENCY")
    use_fixtures: bool = Field(default=False, alias="USE_FIXTURES")

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
            raise ValueError(f"ENVIRONMENT must be one of {sorted(allowed)}")
        return normalized

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_staging(self) -> bool:
        return self.environment == "staging"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def _collect_environment(env_file: Path | None) -> Dict[str, Any]:
    env: Dict[str, Any] = {}
    if env_file is None:
        env_file = _DEFAULT_ENV_FILE
    env.update(_parse_env_file(env_file))
    env.update(os.environ)
    return env


def load_settings(*, env_file: Path | None = None) -> Settings:
    """Load and validate configuration from environment variables."""

    raw_env = _collect_environment(env_file)
    try:
        return Settings.model_validate(raw_env)
    except ValidationError as exc:  # pragma: no cover - configuration errors
        message = ", ".join(err["msg"] for err in exc.errors())
        raise RuntimeError(f"Invalid configuration: {message}") from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""

    env_path = os.getenv(_ENV_FILE_ENV)
    path = Path(env_path) if env_path else _DEFAULT_ENV_FILE
    return load_settings(env_file=path)


__all__ = ["Settings", "get_settings", "load_settings"]
