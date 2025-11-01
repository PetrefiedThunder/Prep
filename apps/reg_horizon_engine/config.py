"""Configuration for the Regulatory Horizon Engine service."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    service_name: str = Field("reg_horizon_engine", description="Service identifier")
    database_url: str = Field(
        "sqlite+aiosqlite:///./rhe.db",
        description="Database connection string used by SQLAlchemy.",
    )
    default_source_confidence: float = Field(
        0.5, description="Fallback confidence score assigned to new sources."
    )
    environment: Literal["local", "dev", "staging", "prod"] = Field(
        "local", description="Deployment environment label."
    )

    class Config:
        env_prefix = "RHE_"
        case_sensitive = False

    @validator("default_source_confidence")
    def _validate_confidence(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("default_source_confidence must be within [0, 1]")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached instance of the service settings."""

    return Settings()
