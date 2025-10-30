"""Core orchestration logic for logistics features."""

from __future__ import annotations

import asyncio
import math
from datetime import datetime, timedelta, timezone

from prep.data_pipeline.cdc import CDCStreamManager
from prep.logistics import schemas
from prep.logistics.onfleet import OnfleetClient, OnfleetConfigurationError, OnfleetError


class LocalRouteOptimizer:
    """Fallback route optimizer using a greedy nearest-neighbour heuristic."""

    def __init__(self, average_speed_kmh: float = 35.0) -> None:
        self._average_speed = max(average_speed_kmh, 1.0)

    async def optimize(self, request: schemas.RouteOptimizationRequest) -> list[schemas.RouteStop]:
        locations = request.stops.copy()
        origin = request.start_location
        now = request.start_time or datetime.now(tz=timezone.utc)
        current_point = origin
        sequence: list[schemas.RouteStop] = []
        for index in range(1, len(locations) + 1):
            next_stop, distance = self._next_stop(current_point, locations)
            if next_stop is None:
                break
            locations.remove(next_stop)
            duration_hours = distance / self._average_speed
            travel_seconds = duration_hours * 3600
            eta = now + timedelta(seconds=travel_seconds)
            sequence.append(
                schemas.RouteStop(
                    id=next_stop.id,
                    eta=eta,
                    sequence=index,
                    travel_distance_meters=distance * 1000,
                    travel_duration_seconds=travel_seconds,
                )
            )
            now = eta + timedelta(minutes=next_stop.service_time_minutes)
            current_point = next_stop.location
        if not sequence:
            raise ValueError("Unable to optimize route with provided stops")
        return sequence

    def _next_stop(
        self, origin: schemas.Coordinate, stops: list[schemas.Stop]
    ) -> tuple[schemas.Stop | None, float]:
        best_stop: schemas.Stop | None = None
        best_distance = math.inf
        for stop in stops:
            distance = self._haversine(origin, stop.location)
            if distance < best_distance:
                best_distance = distance
                best_stop = stop
        if best_stop is None:
            return None, 0.0
        return best_stop, best_distance

    def _haversine(
        self, origin: schemas.Coordinate, destination: schemas.Coordinate
    ) -> float:
        """Return distance in kilometres between two coordinates."""

        radius_km = 6371.0
        lat1 = math.radians(origin.latitude)
        lat2 = math.radians(destination.latitude)
        dlat = lat2 - lat1
        dlon = math.radians(destination.longitude - origin.longitude)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius_km * c


class LogisticsService:
    """Facade that coordinates Onfleet optimization with local fallbacks and CDC."""

    def __init__(
        self,
        onfleet: OnfleetClient,
        cdc_stream: CDCStreamManager,
        optimizer: LocalRouteOptimizer | None = None,
    ) -> None:
        self._onfleet = onfleet
        self._cdc = cdc_stream
        self._optimizer = optimizer or LocalRouteOptimizer()

    async def optimize_route(
        self, request: schemas.RouteOptimizationRequest
    ) -> schemas.RouteOptimizationResponse:
        tasks = []
        source = "onfleet"
        try:
            tasks = await self._onfleet.optimize_route(request)
        except OnfleetConfigurationError:
            source = "local"
            tasks = await self._optimizer.optimize(request)
        except OnfleetError:
            source = "local"
            tasks = await self._optimizer.optimize(request)

        total_distance = sum(stop.travel_distance_meters for stop in tasks)
        total_duration = sum(stop.travel_duration_seconds for stop in tasks)

        await self._emit_cdc_event(request, tasks, source, total_distance, total_duration)

        return schemas.RouteOptimizationResponse(
            vehicle_id=request.vehicle_id,
            stops=tasks,
            total_distance_meters=total_distance,
            total_duration_seconds=total_duration,
            source=source,
        )

    async def _emit_cdc_event(
        self,
        request: schemas.RouteOptimizationRequest,
        stops: list[schemas.RouteStop],
        source: str,
        distance: float,
        duration: float,
    ) -> None:
        payload = {
            "vehicle_id": request.vehicle_id,
            "source": source,
            "total_distance_meters": distance,
            "total_duration_seconds": duration,
            "stop_count": len(stops),
            "soft_capacity": request.soft_capacity,
        }
        schema = {
            "vehicle_id": "string",
            "source": "string",
            "total_distance_meters": "float",
            "total_duration_seconds": "float",
            "stop_count": "integer",
            "soft_capacity": "integer",
        }
        await self._cdc.publish("logistics.route.optimized", payload, schema)


async def build_logistics_service(
    onfleet: OnfleetClient,
    cdc_stream: CDCStreamManager,
) -> LogisticsService:
    """Convenience factory for dependency injection frameworks."""

    # allow cdc stream to perform any asynchronous bootstrapping
    await asyncio.sleep(0)
    return LogisticsService(onfleet=onfleet, cdc_stream=cdc_stream)


__all__ = ["LogisticsService", "LocalRouteOptimizer", "build_logistics_service"]
