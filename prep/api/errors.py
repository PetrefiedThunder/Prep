"""Utilities for producing standardized API error responses."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from prep.platform.schemas import ErrorDetail, ErrorResponseEnvelope, resolve_request_id


def http_error(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
    meta: dict[str, Any] | None = None,
) -> HTTPException:
    """Create an :class:`HTTPException` with the canonical error envelope."""

    envelope = ErrorResponseEnvelope(
        request_id=resolve_request_id(request),
        error=ErrorDetail(code=code, message=message),
        meta=meta,
    )
    return HTTPException(status_code=status_code, detail=envelope.model_dump(), headers=headers)
