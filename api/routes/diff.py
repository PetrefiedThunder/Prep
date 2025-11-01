"""City compliance diff endpoints exposed via the API gateway."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from fastapi import APIRouter, Header, HTTPException, Response

router = APIRouter(prefix="/city/diff", tags=["city-diff"])


def _canonicalize(payload: Mapping[str, Any]) -> bytes:
    """Return a stable JSON encoding for cache keys and ETags."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _etag_for_payload(payload: Mapping[str, Any]) -> str:
    """Compute a strong ETag for the provided payload."""

    digest = hashlib.sha256(_canonicalize(payload)).hexdigest()
    return digest


def _normalize_city(city: str) -> str:
    """Return the canonical slug for a city identifier."""

    return city.strip().lower().replace(" ", "_").replace("-", "_")


_DIFF_DATA: dict[str, dict[str, Any]] = {
    "2024.03.15": {
        "released_at": "2024-03-15T12:00:00Z",
        "summary": "Spring compliance refresh for Bay Area jurisdictions.",
        "jurisdictions": {
            "san_francisco": {
                "added_requirements": [
                    {
                        "id": "SF-FOOD-SAFETY-TRAINING",
                        "title": "Document quarterly food safety refreshers",
                        "severity": "advisory",
                    }
                ],
                "removed_requirements": [],
                "updated_requirements": [
                    {
                        "id": "SF-PLAN-REVIEW",
                        "title": "Plan review submission",
                        "previous": {
                            "agency": "SF Department of Public Health",
                            "processing_time_days": 45,
                        },
                        "current": {
                            "agency": "SF Department of Public Health",
                            "processing_time_days": 30,
                        },
                    }
                ],
                "notes": "Faster processing time based on the new 2024 SLA shared by SFDPH.",
            },
            "oakland": {
                "added_requirements": [],
                "removed_requirements": [
                    {
                        "id": "OAK-ANNUAL-WATER-CERT",
                        "title": "Annual water quality certification",
                    }
                ],
                "updated_requirements": [
                    {
                        "id": "OAK-FIRE-CLEARANCE",
                        "title": "Fire marshal inspection",
                        "previous": {
                            "frequency": "biennial",
                            "contact": "fire_prevention@oaklandca.gov",
                        },
                        "current": {
                            "frequency": "annual",
                            "contact": "fire_inspections@oaklandca.gov",
                        },
                    }
                ],
                "notes": "Aligned with Oakland Fire Department policy bulletin 2024-02.",
            },
        },
    },
    "2024.04.20": {
        "released_at": "2024-04-20T15:30:00Z",
        "summary": "April compliance adjustments and template clean-up.",
        "jurisdictions": {
            "san_francisco": {
                "added_requirements": [],
                "removed_requirements": [],
                "updated_requirements": [
                    {
                        "id": "SF-REINSPECTION-FEE",
                        "title": "Reinspection fee",
                        "previous": {
                            "amount_cents": 30000,
                            "notes": "Applies after initial violation notice",
                        },
                        "current": {
                            "amount_cents": 32500,
                            "notes": "Applies after initial violation notice",
                        },
                    }
                ],
                "notes": "Fee increase reflects July fiscal year adjustments.",
            },
            "berkeley": {
                "added_requirements": [
                    {
                        "id": "BERK-ADA-REPORTING",
                        "title": "Quarterly ADA compliance self-assessment",
                        "severity": "conditional",
                    }
                ],
                "removed_requirements": [],
                "updated_requirements": [],
                "notes": "Berkeley is piloting expanded accessibility reporting for shared kitchens.",
            },
        },
    },
}


def _version_payload(version: str) -> dict[str, Any]:
    """Build the JSON payload returned for a diff version."""

    metadata = _DIFF_DATA.get(version)
    if metadata is None:
        raise KeyError(version)
    payload: dict[str, Any] = {
        "version": version,
        "released_at": metadata["released_at"],
        "summary": metadata["summary"],
        "jurisdictions": metadata["jurisdictions"],
    }
    return payload


def _city_payload(version: str, city: str) -> dict[str, Any]:
    """Return the payload for a specific city within a version."""

    normalized_city = _normalize_city(city)
    metadata = _DIFF_DATA.get(version)
    if metadata is None:
        raise KeyError(version)
    try:
        diff_payload = metadata["jurisdictions"][normalized_city]
    except KeyError as exc:  # pragma: no cover - FastAPI transforms error response
        raise KeyError(normalized_city) from exc
    payload: dict[str, Any] = {
        "version": version,
        "city": normalized_city,
        "released_at": metadata["released_at"],
        "summary": metadata["summary"],
        "diff": diff_payload,
    }
    return payload


@router.get("/versions")
def list_versions() -> dict[str, Any]:
    """Return metadata describing the available diff snapshots."""

    versions: list[dict[str, Any]] = []
    for version, metadata in _DIFF_DATA.items():
        payload = _version_payload(version)
        versions.append(
            {
                "version": version,
                "released_at": metadata["released_at"],
                "jurisdictions": sorted(payload["jurisdictions"].keys()),
                "etag": _etag_for_payload(payload),
            }
        )

    versions.sort(key=lambda item: item["released_at"], reverse=True)
    return {"versions": versions}


@router.get("/{version}")
def get_diff_version(
    version: str,
    if_none_match: str | None = Header(default=None),
) -> Response:
    """Return the diff payload for a specific published version."""

    try:
        payload = _version_payload(version)
    except KeyError as exc:  # pragma: no cover - FastAPI handles conversion
        raise HTTPException(status_code=404, detail=f"Unknown diff version '{version}'") from exc

    etag = _etag_for_payload(payload)
    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status_code=304, headers={"ETag": f'"{etag}"'})

    body = json.dumps(payload)
    return Response(content=body, media_type="application/json", headers={"ETag": f'"{etag}"'})


@router.get("/{version}/{city}")
def get_city_diff(
    version: str,
    city: str,
    if_none_match: str | None = Header(default=None),
) -> Response:
    """Return the diff payload for a specific city within a version."""

    try:
        payload = _city_payload(version, city)
    except KeyError as exc:  # pragma: no cover - FastAPI handles conversion
        if exc.args and exc.args[0] == version:
            raise HTTPException(status_code=404, detail=f"Unknown diff version '{version}'") from exc
        raise HTTPException(status_code=404, detail=f"City '{city}' not found in diff version '{version}'") from exc

    etag = _etag_for_payload(payload)
    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status_code=304, headers={"ETag": f'"{etag}"'})

    body = json.dumps(payload)
    return Response(content=body, media_type="application/json", headers={"ETag": f'"{etag}"'})


__all__ = ["router"]

