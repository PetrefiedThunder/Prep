"""Pydantic models for the Realtime Configuration Service."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class RolloutStrategy(str, Enum):
    """Supported rollout strategies."""

    ALL = "all"
    CANARY = "canary"
    PERCENTAGE = "percentage"


class ConfigRollout(BaseModel):
    """Metadata describing a rollout strategy for a configuration entry."""

    strategy: RolloutStrategy = Field(
        default=RolloutStrategy.ALL,
        description="Rollout strategy used to apply the configuration entry.",
    )
    percent: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Optional percentage of traffic to target when using percentage-based rollouts.",
    )
    metrics_guard: Optional[str] = Field(
        default=None,
        description="Optional expression describing the metric guard that should be satisfied during rollout.",
    )


class ConfigEntry(BaseModel):
    """A configuration entry supplied by clients of the RCS."""

    key: str = Field(..., description="Unique identifier for the configuration entry.")
    state: str = Field(..., description="Desired state for the configuration entry (e.g. 'on', 'off').")
    targeting: Dict[str, Any] = Field(
        default_factory=dict,
        description="Targeting metadata (tenant, geography, role, etc.) that constrains the entry.",
    )
    rollout: Optional[ConfigRollout] = Field(
        default=None,
        description="Rollout metadata describing how to apply this entry incrementally.",
    )
    fallback: Optional[str] = Field(
        default=None,
        description="Fallback state to apply when metric guards or other protections trigger.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata stored alongside the entry.",
    )


class ConfigRecord(ConfigEntry):
    """A persisted configuration entry enriched with storage metadata."""

    version: int = Field(..., description="Monotonic version assigned by the RCS.")
    updated_at: datetime = Field(..., description="Timestamp (UTC) of the most recent update.")


class ChangeType(str, Enum):
    """Change operations that can be emitted by the store."""

    UPSERT = "upsert"
    DELETE = "delete"


class ConfigChange(BaseModel):
    """Represents a change emitted by the configuration store."""

    type: ChangeType
    key: str
    record: Optional[ConfigRecord] = None
    version: int
    emitted_at: datetime


__all__ = [
    "ChangeType",
    "ConfigChange",
    "ConfigEntry",
    "ConfigRecord",
    "ConfigRollout",
    "RolloutStrategy",
]
