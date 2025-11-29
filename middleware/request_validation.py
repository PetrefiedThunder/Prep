"""Request validation middleware for production security.

This module provides:
- Request body size limits
- Content type validation
- Request rate limiting integration
- Input sanitization
- Suspicious request detection
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from prep.observability.logging_config import get_logger

logger = get_logger(__name__)


# Maximum request body sizes by content type (in bytes)
DEFAULT_MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_JSON_BODY_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_FORM_BODY_SIZE = 50 * 1024 * 1024  # 50 MB (for file uploads)
MAX_MULTIPART_BODY_SIZE = 100 * 1024 * 1024  # 100 MB

# Allowed content types
ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "text/plain",
        "text/html",
        "application/xml",
        "text/xml",
    }
)

# Suspicious patterns that might indicate attacks
SUSPICIOUS_PATTERNS = [
    # SQL injection patterns
    re.compile(
        r"(\b(union|select|insert|update|delete|drop|truncate)\b.*\b(from|into|table)\b)",
        re.I,
    ),
    re.compile(r"(-{2}|;)\s*(drop|delete|truncate)", re.I),
    # XSS patterns
    re.compile(r"<script[^>]*>.*?</script>", re.I | re.S),
    re.compile(r"javascript:", re.I),
    re.compile(r"on\w+\s*=", re.I),
    # Path traversal
    re.compile(r"\.\./|\.\.\\"),
    # Command injection
    re.compile(r"[;&|`$]"),
]

# Paths that bypass validation (health checks, etc.)
EXEMPT_PATHS = frozenset(
    {
        "/healthz",
        "/health",
        "/ready",
        "/live",
        "/metrics",
    }
)


class RequestValidationConfig:
    """Configuration for request validation middleware."""

    def __init__(
        self,
        *,
        max_body_size: int = DEFAULT_MAX_BODY_SIZE,
        max_json_size: int = MAX_JSON_BODY_SIZE,
        max_form_size: int = MAX_FORM_BODY_SIZE,
        max_multipart_size: int = MAX_MULTIPART_BODY_SIZE,
        allowed_content_types: frozenset[str] | None = None,
        check_suspicious_patterns: bool = True,
        exempt_paths: frozenset[str] | None = None,
        block_suspicious: bool = False,
    ):
        self.max_body_size = max_body_size
        self.max_json_size = max_json_size
        self.max_form_size = max_form_size
        self.max_multipart_size = max_multipart_size
        self.allowed_content_types = allowed_content_types or ALLOWED_CONTENT_TYPES
        self.check_suspicious_patterns = check_suspicious_patterns
        self.exempt_paths = exempt_paths or EXEMPT_PATHS
        self.block_suspicious = block_suspicious


def get_max_size_for_content_type(
    content_type: str | None,
    config: RequestValidationConfig,
) -> int:
    """Get the maximum allowed body size for a content type."""
    if content_type is None:
        return config.max_body_size

    content_type_lower = content_type.lower().split(";")[0].strip()

    if content_type_lower == "application/json":
        return config.max_json_size
    elif content_type_lower == "application/x-www-form-urlencoded":
        return config.max_form_size
    elif content_type_lower.startswith("multipart/"):
        return config.max_multipart_size

    return config.max_body_size


def check_content_type(
    content_type: str | None,
    config: RequestValidationConfig,
) -> bool:
    """Check if content type is allowed."""
    if content_type is None:
        return True  # No content type is OK for GET requests

    # Extract base content type (without parameters like charset)
    base_type = content_type.lower().split(";")[0].strip()

    # Check for multipart (has boundary parameter)
    if base_type.startswith("multipart/"):
        return "multipart/form-data" in config.allowed_content_types

    return base_type in config.allowed_content_types


def check_suspicious_content(content: str) -> list[str]:
    """Check content for suspicious patterns.

    Returns list of detected pattern descriptions.
    """
    findings: list[str] = []

    for pattern in SUSPICIOUS_PATTERNS:
        if pattern.search(content):
            findings.append(f"Pattern detected: {pattern.pattern[:50]}...")

    return findings


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for validating incoming requests.

    Features:
    - Body size limits
    - Content type validation
    - Suspicious pattern detection
    - Request logging for security monitoring
    """

    def __init__(
        self,
        app: Any,
        config: RequestValidationConfig | None = None,
    ):
        super().__init__(app)
        self.config = config or RequestValidationConfig()

    async def dispatch(
        self,
        request: Request,
        call_next: Any,
    ) -> Response:
        """Process and validate the request."""
        # Skip validation for exempt paths
        if request.url.path in self.config.exempt_paths:
            return await call_next(request)

        # Skip validation for safe methods without body
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        # Get content type and length
        content_type = request.headers.get("content-type")
        content_length_header = request.headers.get("content-length")

        # Validate content type
        if content_type and not check_content_type(content_type, self.config):
            logger.warning(
                f"Blocked request with invalid content type: {content_type}",
                extra={
                    "path": request.url.path,
                    "content_type": content_type,
                    "client_ip": self._get_client_ip(request),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Content type not allowed: {content_type}",
            )

        # Validate content length
        if content_length_header:
            try:
                content_length = int(content_length_header)
                max_size = get_max_size_for_content_type(content_type, self.config)

                if content_length > max_size:
                    logger.warning(
                        f"Blocked request with oversized body: {content_length} > {max_size}",
                        extra={
                            "path": request.url.path,
                            "content_length": content_length,
                            "max_size": max_size,
                            "client_ip": self._get_client_ip(request),
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request body too large: {content_length} bytes (max: {max_size})",
                    )
            except ValueError:
                logger.warning(
                    f"Invalid content-length header: {content_length_header}",
                    extra={"path": request.url.path},
                )

        # Check for suspicious patterns in URL and headers
        if self.config.check_suspicious_patterns:
            # Check URL path and query string
            url_to_check = (
                f"{request.url.path}?{request.url.query}"
                if request.url.query
                else request.url.path
            )

            findings = check_suspicious_content(url_to_check)
            if findings:
                logger.warning(
                    f"Suspicious URL pattern detected: {findings}",
                    extra={
                        "path": request.url.path,
                        "findings": findings,
                        "client_ip": self._get_client_ip(request),
                    },
                )

                if self.config.block_suspicious:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid request",
                    )

            # Check selected headers
            user_agent = request.headers.get("user-agent", "")
            referer = request.headers.get("referer", "")

            for header_value in [user_agent, referer]:
                if header_value:
                    header_findings = check_suspicious_content(header_value)
                    if header_findings:
                        logger.warning(
                            f"Suspicious header content detected: {header_findings}",
                            extra={
                                "path": request.url.path,
                                "findings": header_findings,
                                "client_ip": self._get_client_ip(request),
                            },
                        )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"


def validate_json_payload(
    data: dict[str, Any],
    *,
    max_depth: int = 10,
    max_keys: int = 100,
    max_string_length: int = 10000,
) -> list[str]:
    """Validate JSON payload structure and content.

    Returns list of validation errors.
    """
    errors: list[str] = []

    def check_value(value: Any, depth: int, path: str) -> None:
        if depth > max_depth:
            errors.append(f"Maximum nesting depth exceeded at {path}")
            return

        if isinstance(value, dict):
            if len(value) > max_keys:
                errors.append(f"Too many keys ({len(value)}) at {path}")
            for key, val in value.items():
                check_value(val, depth + 1, f"{path}.{key}")
        elif isinstance(value, list):
            for i, item in enumerate(value):
                check_value(item, depth + 1, f"{path}[{i}]")
        elif isinstance(value, str):
            if len(value) > max_string_length:
                errors.append(f"String too long ({len(value)} chars) at {path}")
            # Check for suspicious patterns in strings
            findings = check_suspicious_content(value)
            if findings:
                errors.append(f"Suspicious content at {path}: {findings}")

    check_value(data, 0, "root")
    return errors


__all__ = [
    "RequestValidationConfig",
    "RequestValidationMiddleware",
    "check_content_type",
    "check_suspicious_content",
    "get_max_size_for_content_type",
    "validate_json_payload",
]
