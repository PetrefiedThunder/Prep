"""City regulatory diff endpoints."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from api.routes._city_utils import SUPPORTED_CITIES, normalize_city

router = APIRouter(prefix="/city/diff", tags=["city", "diff"])


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _change(kind: str, text: str, *, previous_text: str | None = None, section: str = "health") -> dict[str, Any]:
    change: dict[str, Any] = {
        "type": kind,
        "section": section,
        "para_hash": _hash_text(f"{section}:{text}"),
        "text": text,
    }
    if previous_text is not None:
        change["previous_text"] = previous_text
    return change


def _compute_etag(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"W/\"{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}\""


def _build_history(city_norm: str) -> list[dict[str, Any]]:
    readable = city_norm.replace("_", " ").title()
    history = [
        {
            "city": city_norm,
            "version": "2024.05.01",
            "previous_version": "2024.02.15",
            "generated_at": "2024-05-01T08:00:00Z",
            "summary": f"{readable} updated permit fees and safety training cadence.",
            "changes": [
                _change(
                    "modified",
                    f"Annual health permit fee increased to $1,040 for {readable}.",
                    previous_text="Annual health permit fee was $980.",
                    section="fees",
                ),
                _change(
                    "added",
                    f"Quarterly food safety training logs must be retained for {readable} operators.",
                    section="operations",
                ),
            ],
        },
        {
            "city": city_norm,
            "version": "2024.02.15",
            "previous_version": "2023.11.01",
            "generated_at": "2024-02-15T07:30:00Z",
            "summary": f"{readable} shortened the grace period for corrective actions after inspections.",
            "changes": [
                _change(
                    "modified",
                    f"Follow-up inspection window reduced to 10 days in {readable}.",
                    previous_text="Operators previously had 14 days to schedule reinspection.",
                    section="inspections",
                ),
            ],
        },
    ]

    for record in history:
        base = {
            "city": record["city"],
            "version": record["version"],
            "previous_version": record["previous_version"],
            "summary": record["summary"],
            "changes": record["changes"],
        }
        record["etag"] = _compute_etag(base)
    return history


_HISTORY_BY_CITY: dict[str, list[dict[str, Any]]] = {city: _build_history(city) for city in SUPPORTED_CITIES}


def _select_record(city_norm: str, version: str | None) -> dict[str, Any]:
    try:
        history = _HISTORY_BY_CITY[city_norm]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unsupported city '{city_norm}'") from exc

    if version is None:
        return history[0]

    for record in history:
        if record["version"] == version:
            return record

    raise HTTPException(status_code=404, detail=f"Unknown version '{version}' for city '{city_norm}'")


def _build_versions(city_norm: str) -> list[str]:
    return [record["version"] for record in _HISTORY_BY_CITY[city_norm]]


def _evaluate_conditional_request(record: dict[str, Any], request: Request) -> Response | None:
    if_none_match = request.headers.get("if-none-match")
    if if_none_match:
        candidates = {candidate.strip() for candidate in if_none_match.split(",")}
        if "*" in candidates or record["etag"] in candidates:
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": record["etag"]})
    return None


@router.get("/{city}")
def get_city_diff(city: str, request: Request, version: str | None = None):
    try:
        city_norm = normalize_city(city)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unsupported city '{city}'") from exc

    record = _select_record(city_norm, version)

    conditional = _evaluate_conditional_request(record, request)
    if conditional is not None:
        return conditional

    payload = {
        "city": record["city"],
        "version": record["version"],
        "previous_version": record["previous_version"],
        "generated_at": record["generated_at"],
        "summary": record["summary"],
        "changes": record["changes"],
        "available_versions": _build_versions(city_norm),
    }

    response = JSONResponse(payload)
    response.headers["ETag"] = record["etag"]
    response.headers["X-Prep-Diff-Version"] = record["version"]
    response.headers["Cache-Control"] = "public, max-age=300"
    return response


@router.head("/{city}")
def head_city_diff(city: str, request: Request, version: str | None = None) -> Response:
    try:
        city_norm = normalize_city(city)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unsupported city '{city}'") from exc

    record = _select_record(city_norm, version)
    conditional = _evaluate_conditional_request(record, request)
    if conditional is not None:
        return conditional

    headers = {"ETag": record["etag"], "X-Prep-Diff-Version": record["version"], "Cache-Control": "public, max-age=300"}
    return Response(status_code=status.HTTP_200_OK, headers=headers)
