from __future__ import annotations

from datetime import UTC, datetime

import pytest

from prep.data_pipeline.cdc import build_cdc_stream
from prep.logistics import schemas
from prep.logistics.onfleet import OnfleetClient
from prep.logistics.service import LogisticsService
from prep.settings import Settings


@pytest.mark.asyncio
async def test_logistics_service_falls_back_to_local_solver() -> None:
    settings = Settings()
    cdc = build_cdc_stream(settings)
    service = LogisticsService(
        onfleet=OnfleetClient(base_url="https://example.com", api_key=None),
        cdc_stream=cdc,
    )
    request = schemas.RouteOptimizationRequest(
        vehicle_id="vehicle-1",
        start_location=schemas.Coordinate(latitude=40.7128, longitude=-74.0060),
        start_time=datetime(2024, 1, 1, 12, tzinfo=UTC),
        stops=[
            schemas.Stop(
                id="1",
                location=schemas.Coordinate(latitude=40.73061, longitude=-73.935242),
                service_time_minutes=5,
            ),
            schemas.Stop(
                id="2",
                location=schemas.Coordinate(latitude=40.650002, longitude=-73.949997),
                service_time_minutes=7,
            ),
        ],
    )

    response = await service.optimize_route(request)

    assert response.source == "local"
    assert len(response.stops) == 2
    assert response.total_distance_meters > 0
    assert response.total_duration_seconds > 0
    # Because analytics destinations are not configured in default settings.
    assert not cdc.bigquery.events
    assert not cdc.snowflake.events
