"""Integration-style tests for the SF data drift audit script."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts import audit_upstream_drift


def _write_records(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(records), encoding="utf-8")


def test_main_generates_metrics_with_mocked_upstream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_path = tmp_path / "dataset.json"
    records = [
        {"value": 1, "notes": "ok"},
        {"value": None, "notes": "   "},
    ]
    _write_records(dataset_path, records)

    ingestion_timestamp = datetime(2024, 1, 1, tzinfo=UTC)
    os.utime(dataset_path, (ingestion_timestamp.timestamp(), ingestion_timestamp.timestamp()))

    reference_timestamp = ingestion_timestamp - timedelta(hours=12)

    @dataclass
    class FakeUpstreamRecord:
        value: int
        observed_at: datetime

    class FakeClient:
        def fetch(self) -> FakeUpstreamRecord:
            return FakeUpstreamRecord(value=99, observed_at=reference_timestamp)

    spec = audit_upstream_drift.DatasetSpec(
        name="fake_dataset",
        loader=lambda: json.loads(dataset_path.read_text(encoding="utf-8")),
        modtime_path=dataset_path,
        upstream_client_factory=FakeClient,
        upstream_call=lambda client: client.fetch(),
        expected_dataclass=FakeUpstreamRecord,
    )

    monkeypatch.setattr(
        audit_upstream_drift,
        "_utcnow",
        lambda: ingestion_timestamp + timedelta(hours=24),
    )

    output_path = tmp_path / "report.csv"
    rows = audit_upstream_drift.main(output_path=output_path, dataset_specs=[spec])

    assert output_path.exists()
    assert "fake_dataset" in output_path.read_text(encoding="utf-8")

    assert len(rows) == 1
    row = rows[0]
    assert row["dataset"] == "fake_dataset"
    assert row["record_count"] == 2
    assert row["local_field_count"] == 2
    assert row["upstream_field_count"] == 2
    assert row["field_count_match"] is True
    assert row["ingestion_last_updated"] == ingestion_timestamp.isoformat()
    assert row["ingestion_age_hours"] == pytest.approx(24.0)
    assert row["upstream_call_latency_ms"] is not None
    assert row["upstream_reference_field"] == "observed_at"
    assert row["upstream_reference_timestamp"] == reference_timestamp.isoformat()
    assert row["staleness_vs_upstream_hours"] == pytest.approx(12.0)
    null_rates = json.loads(row["null_rates"])
    assert null_rates["notes"] == pytest.approx(0.5)
    assert null_rates["value"] == pytest.approx(0.5)
    assert row["upstream_error"] is None


def test_collect_dataset_metrics_captures_upstream_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_path = tmp_path / "error_dataset.json"
    _write_records(dataset_path, [{"code": "A"}])

    ingestion_timestamp = datetime(2024, 2, 1, tzinfo=UTC)
    os.utime(dataset_path, (ingestion_timestamp.timestamp(), ingestion_timestamp.timestamp()))

    @dataclass
    class SimpleRecord:
        code: str

    spec = audit_upstream_drift.DatasetSpec(
        name="error_dataset",
        loader=lambda: json.loads(dataset_path.read_text(encoding="utf-8")),
        modtime_path=dataset_path,
        upstream_client_factory=lambda: object(),
        upstream_call=lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
        expected_dataclass=SimpleRecord,
    )

    monkeypatch.setattr(
        audit_upstream_drift,
        "_utcnow",
        lambda: ingestion_timestamp + timedelta(hours=1),
    )

    row = audit_upstream_drift.collect_dataset_metrics(spec)

    assert row["dataset"] == "error_dataset"
    assert row["record_count"] == 1
    assert row["local_field_count"] == 1
    assert row["upstream_field_count"] == 1
    assert row["field_count_match"] is True
    assert row["ingestion_last_updated"] == ingestion_timestamp.isoformat()
    assert row["ingestion_age_hours"] == pytest.approx(1.0)
    assert row["upstream_call_latency_ms"] is None
    assert row["upstream_reference_field"] is None
    assert row["upstream_reference_timestamp"] is None
    assert row["staleness_vs_upstream_hours"] is None
    assert json.loads(row["null_rates"]) == {"code": 0.0}
    assert row["upstream_error"] == "boom"
