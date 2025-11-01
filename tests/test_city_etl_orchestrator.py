"""Tests for the City ETL orchestrator service."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytest.importorskip(
    "prometheus_client",
    reason="prometheus_client is required to validate orchestrator metrics",
)
from prometheus_client import REGISTRY


def _reload_modules() -> tuple:
    """Reload database and orchestrator modules against a temporary database."""

    database = importlib.import_module("apps.sf_regulatory_service.database")
    database = importlib.reload(database)

    models = importlib.import_module("apps.sf_regulatory_service.models")
    models = importlib.reload(models)

    database.init_db()

    orchestrator_metrics = importlib.import_module("apps.city_etl_orchestrator.metrics")
    orchestrator_metrics = importlib.reload(orchestrator_metrics)

    orchestrator_module = importlib.import_module("apps.city_etl_orchestrator.orchestrator")
    orchestrator_module = importlib.reload(orchestrator_module)

    return database, models, orchestrator_module, orchestrator_metrics


def _set_sqlite_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    db_path = tmp_path / "sf_regulatory.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("SF_DATABASE_URL", url)
    return url


def _collect_metric(metric, labels: dict) -> float:
    for sample in metric.collect()[0].samples:
        if sample.labels == labels:
            return sample.value
    raise AssertionError(f"Metric sample with labels {labels} not found")


@pytest.fixture(autouse=True)
def clear_prometheus_registry():
    """Reset the default Prometheus registry between tests."""

    collectors = list(REGISTRY._collector_to_names.keys())  # type: ignore[attr-defined]
    for collector in collectors:
        REGISTRY.unregister(collector)

    yield

    collectors = list(REGISTRY._collector_to_names.keys())  # type: ignore[attr-defined]
    for collector in collectors:
        REGISTRY.unregister(collector)


def test_orchestrated_run_records_metrics_and_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_sqlite_url(tmp_path, monkeypatch)
    database, models, orchestrator_module, metrics_module = _reload_modules()

    orchestrator = orchestrator_module.CityEtlOrchestrator(
        session_factory=database.SessionLocal,
        interval_seconds=9999,
    )

    result = orchestrator.run_once()
    assert result.status == "success"

    session = database.SessionLocal()
    try:
        rows = session.query(models.CityEtlRun).all()
    finally:
        session.close()
    assert len(rows) == 1
    assert rows[0].city == "San Francisco"
    assert rows[0].status == "success"

    success_count = _collect_metric(
        metrics_module.city_etl_runs_total,
        {"city": "San Francisco", "status": "success"},
    )
    assert success_count == 1.0

    last_success = _collect_metric(
        metrics_module.city_etl_last_success_timestamp,
        {"city": "San Francisco"},
    )
    assert last_success > 0


def test_trigger_endpoint_runs_etl_and_exposes_metrics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_sqlite_url(tmp_path, monkeypatch)
    database, _, orchestrator_module, _ = _reload_modules()
    monkeypatch.setenv("CITY_ETL_INTERVAL_SECONDS", "99999")

    # Prevent background scheduling during the test to avoid flakiness.
    monkeypatch.setattr(orchestrator_module.CityEtlOrchestrator, "start", lambda self: None)
    monkeypatch.setattr(orchestrator_module.CityEtlOrchestrator, "stop", lambda self: None)

    main_module = importlib.import_module("apps.city_etl_orchestrator.main")
    main_module = importlib.reload(main_module)

    app = main_module.create_app()
    with TestClient(app) as client:
        trigger_response = client.post("/runs/trigger")
        assert trigger_response.status_code == 200

        health_response = client.get("/health")
        assert health_response.status_code == 200
        health = health_response.json()
        assert health["last_run_status"] == "success"
        assert health["status"] == "ok"

        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        assert "city_etl_runs_total" in metrics_response.text
