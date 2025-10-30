"""Utilities for Spark Structured Streaming jobs in the Prep data plane."""
from __future__ import annotations

import importlib
import importlib.util
import os
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict

SCHEMA_SUBJECT_TO_FILE: Dict[str, str] = {
    "prep.pos.PosTxn": "pos_txn.avsc",
    "prep.delivery.DeliveryStatus": "delivery_status.avsc",
    "prep.optimizer.Decision": "decision_event.avsc",
}


def _default_schema_root() -> Path:
    root = os.getenv("SCHEMA_REGISTRY_DIR")
    if root:
        return Path(root)
    return Path(__file__).resolve().parents[1] / "contracts" / "avro"


@lru_cache(maxsize=None)
def load_avro_schema(subject: str, *, schema_root: Path | None = None) -> str:
    """Load an Avro schema for a given Schema Registry subject."""
    file_name = SCHEMA_SUBJECT_TO_FILE.get(subject)
    if not file_name:
        raise ValueError(f"Unsupported schema subject: {subject}")

    base_path = schema_root or _default_schema_root()
    schema_path = base_path / file_name
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    return schema_path.read_text(encoding="utf-8")


def resolve_ge_validator() -> Callable:
    spec = importlib.util.find_spec("great_expectations_provider")
    if spec is None:
        def _noop(df, suite: str, on_fail: str, **kwargs):  # type: ignore[override]
            return df
        return _noop
    module = importlib.import_module("great_expectations_provider")
    return getattr(module, "ge_validate")


ge_validate = resolve_ge_validator()
