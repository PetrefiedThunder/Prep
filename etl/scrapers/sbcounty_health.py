"""Seed loader for San Bernardino County health permit requirements."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Iterable, Mapping

from sqlalchemy.orm import Session

from prep.models.db import session_scope
from prep.regulatory.loader import load_regdoc

LOGGER = logging.getLogger(__name__)

_COUNTY_NAME = "San Bernardino County"
_STATE = "CA"
_DEFAULT_SEED_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "state" / "ca_san_bernardino_requirements.json"
)


def _load_seed(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")

    if path.suffix.lower() != ".json":
        raise ValueError(f"Unsupported seed format for {path}; expected a JSON array of requirement rows")

    with path.open("r", encoding="utf-8") as seed_file:
        data = json.load(seed_file)

    if not isinstance(data, list):
        raise ValueError("Seed JSON must be an array of requirement objects")

    normalized_rows: list[dict[str, Any]] = []
    for index, row in enumerate(data, start=1):
        if not isinstance(row, Mapping):
            raise ValueError(f"Seed row at index {index} is not an object: {row!r}")
        normalized_rows.append(dict(row))

    return normalized_rows


def _hash_row(row: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        {
            "name": row.get("name"),
            "description": row.get("description"),
            "source_url": row.get("source_url"),
            "jurisdiction": row.get("jurisdiction"),
            "expiration_interval": row.get("expiration_interval"),
            "cert_type": row.get("cert_type"),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _normalize(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    payload.setdefault("county", _COUNTY_NAME)

    normalized: dict[str, Any] = {
        "sha256_hash": _hash_row(row),
        "jurisdiction": row.get("jurisdiction") or f"{_COUNTY_NAME}, {_STATE}",
        "state": _STATE,
        "doc_type": row.get("cert_type"),
        "title": row.get("name"),
        "summary": row.get("description"),
        "source_url": row.get("source_url"),
        "raw_payload": payload,
    }

    # Remove optional fields that are empty to keep load_regdoc payloads clean.
    for key in ("summary", "source_url"):
        if not normalized.get(key):
            normalized.pop(key, None)

    return normalized


def _prepare_regdocs(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    regdocs = [_normalize(row) for row in rows]
    LOGGER.debug("Prepared %d San Bernardino County requirement rows", len(regdocs))
    return regdocs


def load_san_bernardino_requirements(
    *,
    seed_path: Path | None = None,
    session: Session | None = None,
) -> dict[str, int]:
    """Load San Bernardino County requirements into the regulatory store."""

    resolved_seed_path = Path(seed_path) if seed_path else _DEFAULT_SEED_PATH
    rows = _load_seed(resolved_seed_path)
    regdocs = _prepare_regdocs(rows)

    if not regdocs:
        LOGGER.info("No San Bernardino County requirements found in %s", resolved_seed_path)
        return {"processed": 0, "inserted": 0}

    if session is None:
        with session_scope() as scoped_session:
            inserted = load_regdoc(scoped_session, regdocs)
    else:
        inserted = load_regdoc(session, regdocs)

    summary = {"processed": len(regdocs), "inserted": inserted}
    LOGGER.info(
        "Loaded San Bernardino County requirements from %s (processed=%d, inserted=%d)",
        resolved_seed_path,
        summary["processed"],
        summary["inserted"],
    )
    return summary


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    summary = load_san_bernardino_requirements()
    LOGGER.info("San Bernardino County ETL summary: %s", summary)


if __name__ == "__main__":
    main()
