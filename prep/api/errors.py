"""Shared helpers for producing structured API error responses."""

from __future__ import annotations

from typing import Any, Mapping
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from prep.platform.schemas import ErrorDetail, ErrorResponse


def _resolve_request_id(request: Request) -> str:
    """Return the request identifier, preferring client-specified values."""

    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return request_id

    header_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
    if header_id:
        request.state.request_id = header_id
        return header_id

    generated = str(uuid4())
    request.state.request_id = generated
    return generated


def _build_error_detail(
    *,
    code: str,
    message: str,
    target: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ErrorDetail:
    return ErrorDetail(
        code=code,
        message=message,
        target=target,
        metadata=dict(metadata) if metadata else None,
    )


def http_exception(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    target: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> HTTPException:
    """Create an ``HTTPException`` carrying the canonical error envelope."""

    request_id = _resolve_request_id(request)
    envelope = ErrorResponse(
        request_id=request_id,
        error=_build_error_detail(code=code, message=message, target=target, metadata=metadata),
    )

    response_headers = {"X-Request-ID": request_id}
    if headers:
        response_headers.update(headers)

    return HTTPException(status_code=status_code, detail=envelope.model_dump(), headers=response_headers)


def json_error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    target: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Return a ``JSONResponse`` carrying the canonical error envelope."""

    request_id = _resolve_request_id(request)
    envelope = ErrorResponse(
        request_id=request_id,
        error=_build_error_detail(code=code, message=message, target=target, metadata=metadata),
    )

    response = JSONResponse(status_code=status_code, content=envelope.model_dump())
    response.headers.setdefault("X-Request-ID", request_id)
    if headers:
        for key, value in headers.items():
            response.headers.setdefault(key, value)
    return response


__all__ = ["http_exception", "json_error_response"]
