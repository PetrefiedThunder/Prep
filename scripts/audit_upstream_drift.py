"""Generate a drift summary comparing ingested SF datasets with upstream schemas."""

from __future__ import annotations

import csv
import dataclasses
import importlib.util
import json
import sys
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterable, Mapping, Sequence

from apps.sf_regulatory_service import config as sf_config


DEFAULT_OUTPUT_PATH = Path("audits/data/SF_Data_Drift_Dashboard.csv")


def _utcnow() -> datetime:
    """Return a timezone-aware ``datetime`` in UTC."""

    return datetime.now(timezone.utc)


def _coerce_datetime(value: Any) -> datetime | None:
    """Convert ``value`` into an aware ``datetime`` when possible."""

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    return None


def _load_json_records(path: Path) -> list[dict[str, Any]]:
    """Read a JSON list of mappings from *path*."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected list of objects in {path}")
    normalised: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, Mapping):
            raise ValueError(f"Expected mapping entries in {path}")
        normalised.append(dict(item))
    return normalised


def _load_health_permit_mappings() -> list[dict[str, Any]]:
    """Return structured rows for the SF health permit facility mapping."""

    config = sf_config.load_config()
    compliance = config.get("compliance", {})
    health_cfg = compliance.get("health_permit", {})
    mapping: Mapping[str, str] = health_cfg.get("facility_type_mapping", {})  # type: ignore[assignment]
    statuses: Iterable[str] = health_cfg.get("valid_statuses", [])  # type: ignore[assignment]
    expiration_warning = health_cfg.get("expiration_warning_days")

    status_value = ", ".join(sorted(statuses)) if statuses else None
    rows: list[dict[str, Any]] = []
    for facility, expected_permit in sorted(mapping.items()):
        rows.append(
            {
                "facility_type": facility,
                "expected_permit": expected_permit,
                "valid_statuses": status_value,
                "expiration_warning_days": expiration_warning,
            }
        )
    return rows


def _collect_field_names(records: Sequence[Mapping[str, Any]]) -> list[str]:
    field_names: set[str] = set()
    for record in records:
        field_names.update(record.keys())
    return sorted(field_names)


def _compute_null_rates(records: Sequence[Mapping[str, Any]], field_names: Sequence[str]) -> dict[str, float]:
    if not records:
        return {}
    null_counts = {field: 0 for field in field_names}
    for record in records:
        for field in field_names:
            value = record.get(field)
            if value is None:
                null_counts[field] += 1
                continue
            if isinstance(value, str) and not value.strip():
                null_counts[field] += 1
                continue
    total = float(len(records))
    return {field: null_counts[field] / total for field in field_names}


def _extract_reference_timestamp(result: Any) -> tuple[str, datetime] | None:
    """Best-effort extraction of a timestamp field from ``result``."""

    if result is None:
        return None
    if dataclasses.is_dataclass(result):
        for field in dataclasses.fields(result):
            value = getattr(result, field.name)
            coerced = _coerce_datetime(value)
            if coerced is not None:
                return field.name, coerced
        return None
    if isinstance(result, Mapping):
        for key, value in result.items():
            coerced = _coerce_datetime(value)
            if coerced is not None:
                return str(key), coerced
    return None


@dataclass(frozen=True)
class DatasetSpec:
    """Configuration describing a dataset to audit."""

    name: str
    loader: Callable[[], list[dict[str, Any]]]
    modtime_path: Path
    upstream_client_factory: Callable[[], Any]
    upstream_call: Callable[[Any], Any]
    expected_dataclass: type[Any]


@lru_cache(maxsize=1)
def _load_sf_modules() -> tuple[type[Any], type[Any], type[Any], type[Any]]:
    """Load SF integration clients without importing the package namespace."""

    base_dir = Path(__file__).resolve().parents[1]

    def _load(module_name: str, relative_path: str) -> ModuleType:
        module_path = base_dir / relative_path
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load module {module_name} from {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    planning_module = _load(
        "_sf_planning_api_module",
        "integrations/sf/sf_planning_api.py",
    )
    health_module = _load(
        "_sf_health_api_module",
        "integrations/sf/sf_health_api.py",
    )

    planning_client = getattr(planning_module, "SanFranciscoPlanningAPI")
    zoning_result = getattr(planning_module, "ZoningLookupResult")
    health_client = getattr(health_module, "SanFranciscoHealthAPI")
    health_record = getattr(health_module, "HealthPermitRecord")
    return planning_client, zoning_result, health_client, health_record


def collect_dataset_metrics(spec: DatasetSpec) -> dict[str, Any]:
    """Return a metrics row for *spec*."""

    records = spec.loader()
    field_names = _collect_field_names(records)
    local_field_count = len(field_names)

    schema_fields = dataclasses.fields(spec.expected_dataclass)
    upstream_field_count = len(schema_fields)

    null_rates = _compute_null_rates(records, field_names)

    try:
        stat_result = spec.modtime_path.stat()
        ingestion_timestamp = datetime.fromtimestamp(stat_result.st_mtime, tz=UTC)
    except FileNotFoundError:
        ingestion_timestamp = _utcnow()

    now = _utcnow()
    ingestion_age_hours = (now - ingestion_timestamp).total_seconds() / 3600.0

    upstream_error: str | None = None
    upstream_latency_ms: float | None = None
    upstream_reference_field: str | None = None
    upstream_reference_timestamp: datetime | None = None

    try:
        client = spec.upstream_client_factory()
        start = time.perf_counter()
        result = spec.upstream_call(client)
        upstream_latency_ms = (time.perf_counter() - start) * 1000.0
        reference = _extract_reference_timestamp(result)
        if reference is not None:
            upstream_reference_field, upstream_reference_timestamp = reference
    except Exception as exc:  # pragma: no cover - defensive guard
        upstream_error = str(exc)

    staleness_vs_upstream_hours: float | None = None
    if upstream_reference_timestamp is not None:
        staleness_vs_upstream_hours = (ingestion_timestamp - upstream_reference_timestamp).total_seconds() / 3600.0

    row = {
        "dataset": spec.name,
        "record_count": len(records),
        "local_field_count": local_field_count,
        "upstream_field_count": upstream_field_count,
        "field_count_match": local_field_count == upstream_field_count,
        "ingestion_last_updated": ingestion_timestamp.isoformat(),
        "ingestion_age_hours": round(ingestion_age_hours, 4),
        "upstream_call_latency_ms": round(upstream_latency_ms, 4) if upstream_latency_ms is not None else None,
        "upstream_reference_field": upstream_reference_field,
        "upstream_reference_timestamp": upstream_reference_timestamp.isoformat()
        if upstream_reference_timestamp
        else None,
        "staleness_vs_upstream_hours": round(staleness_vs_upstream_hours, 4)
        if staleness_vs_upstream_hours is not None
        else None,
        "null_rates": json.dumps({field: round(rate, 4) for field, rate in null_rates.items()}, sort_keys=True),
        "upstream_error": upstream_error,
    }
    return row


def build_dataset_specs() -> list[DatasetSpec]:
    """Return the dataset specifications for San Francisco audits."""

    zoning_path = Path("regengine/cities/san_francisco/fixtures/zoning_codes.json")
    health_config_path = sf_config.CONFIG_PATH

    (
        planning_client,
        zoning_result,
        health_client,
        health_record,
    ) = _load_sf_modules()

    specs = [
        DatasetSpec(
            name="zoning",
            loader=lambda path=zoning_path: _load_json_records(path),
            modtime_path=zoning_path,
            upstream_client_factory=planning_client,
            upstream_call=lambda client: client.resolve("123 Market St, San Francisco, CA"),
            expected_dataclass=zoning_result,
        ),
        DatasetSpec(
            name="health_permits",
            loader=_load_health_permit_mappings,
            modtime_path=health_config_path,
            upstream_client_factory=health_client,
            upstream_call=lambda client: client.lookup_permit(
                "HP-0001234", "cooking_kitchen", "123 Market St, San Francisco, CA"
            ),
            expected_dataclass=health_record,
        ),
    ]
    return specs


def generate_report(specs: Sequence[DatasetSpec]) -> list[dict[str, Any]]:
    """Collect metrics rows for each dataset specification."""

    rows: list[dict[str, Any]] = []
    for spec in specs:
        rows.append(collect_dataset_metrics(spec))
    return rows


def write_csv(rows: Sequence[Mapping[str, Any]], output_path: Path) -> None:
    """Serialize *rows* into *output_path* as CSV."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "dataset",
        "record_count",
        "local_field_count",
        "upstream_field_count",
        "field_count_match",
        "ingestion_last_updated",
        "ingestion_age_hours",
        "upstream_call_latency_ms",
        "upstream_reference_field",
        "upstream_reference_timestamp",
        "staleness_vs_upstream_hours",
        "null_rates",
        "upstream_error",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main(
    *,
    output_path: Path | None = None,
    dataset_specs: Sequence[DatasetSpec] | None = None,
) -> list[dict[str, Any]]:
    """Entry point used by CLI and tests."""

    specs = list(dataset_specs) if dataset_specs is not None else build_dataset_specs()
    rows = generate_report(specs)
    destination = output_path or DEFAULT_OUTPUT_PATH
    write_csv(rows, destination)
    return rows


if __name__ == "__main__":  # pragma: no cover - CLI invocation
    main()


__all__ = [
    "DatasetSpec",
    "collect_dataset_metrics",
    "build_dataset_specs",
    "generate_report",
    "main",
    "write_csv",
]
