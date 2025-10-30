"""Typed request/response contracts for logistics orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, confloat, conint, validator


class Coordinate(BaseModel):
    """Geographic coordinate used by optimization engines."""

    latitude: confloat(ge=-90, le=90)  # type: ignore[valid-type]
    longitude: confloat(ge=-180, le=180)  # type: ignore[valid-type]


class Stop(BaseModel):
    """Delivery or pickup waypoint to include in an optimized route."""

    id: str = Field(..., description="Unique identifier for the stop")
    location: Coordinate
    service_time_minutes: conint(ge=1, le=240) = Field(
        default=10, description="Expected service duration at the stop"
    )
    due_at: datetime | None = Field(
        default=None, description="Latest timestamp the stop should be serviced"
    )
    type: Literal["pickup", "dropoff"] = Field(default="dropoff")


class RouteOptimizationRequest(BaseModel):
    """Payload accepted by the ``/logistics/route`` endpoint."""

    vehicle_id: str
    start_location: Coordinate
    stops: list[Stop]
    soft_capacity: conint(ge=1, le=500) = Field(
        default=50, description="Nominal capacity of the route vehicle"
    )
    start_time: datetime | None = Field(
        default=None, description="When the route should begin"
    )

    @validator("stops")
    def _validate_stops(cls, value: list[Stop]) -> list[Stop]:
        if not value:
            raise ValueError("At least one stop must be provided for optimization")
        return value


class RouteStop(BaseModel):
    """Normalized representation of a stop returned by Onfleet or local solver."""

    id: str
    eta: datetime | None
    sequence: conint(ge=1)
    travel_distance_meters: float
    travel_duration_seconds: float


class RouteOptimizationResponse(BaseModel):
    """Response emitted by ``/logistics/route`` describing the computed route."""

    vehicle_id: str
    stops: list[RouteStop]
    total_distance_meters: float
    total_duration_seconds: float
    source: Literal["onfleet", "local"]


__all__ = [
    "Coordinate",
    "Stop",
    "RouteOptimizationRequest",
    "RouteOptimizationResponse",
    "RouteStop",
]
