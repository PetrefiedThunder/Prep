"""Structured JSON logging configuration for production observability.

This module provides centralized logging configuration with:
- JSON-formatted output for log aggregation (ELK, Loki, etc.)
- Correlation IDs for request tracing
- Performance metrics in log entries
- Configurable log levels per module
- Sensitive data masking
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable for request correlation
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
request_context_var: ContextVar[dict[str, Any]] = ContextVar(
    "request_context", default={}
)


# Sensitive field patterns to mask
SENSITIVE_FIELDS = frozenset(
    {
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "credential",
        "private_key",
        "access_token",
        "refresh_token",
        "jwt",
        "ssn",
        "social_security",
        "credit_card",
        "card_number",
        "cvv",
        "pin",
    }
)


def mask_sensitive_data(data: Any, depth: int = 0) -> Any:
    """Recursively mask sensitive fields in data structures.

    Args:
        data: The data to mask
        depth: Current recursion depth (prevents infinite recursion)

    Returns:
        Data with sensitive fields masked
    """
    if depth > 10:  # Prevent infinite recursion
        return "[MAX_DEPTH_EXCEEDED]"

    if isinstance(data, dict):
        return {
            k: (
                "[REDACTED]"
                if k.lower() in SENSITIVE_FIELDS
                else mask_sensitive_data(v, depth + 1)
            )
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive_data(item, depth + 1) for item in data]
    elif isinstance(data, str):
        # Check if it looks like a JWT or API key
        if data.startswith("eyJ") and "." in data:
            return "[REDACTED_JWT]"
        if len(data) > 20 and data.isalnum():
            return "[REDACTED_KEY]"
    return data


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging.

    Outputs log records as single-line JSON objects suitable for
    log aggregation systems like ELK, Loki, or CloudWatch.
    """

    def __init__(
        self,
        *,
        include_timestamp: bool = True,
        include_logger: bool = True,
        include_level: bool = True,
        include_module: bool = True,
        include_function: bool = True,
        include_line: bool = True,
        include_process: bool = False,
        include_thread: bool = False,
        timestamp_format: str = "iso",
        extra_fields: dict[str, Any] | None = None,
    ):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_logger = include_logger
        self.include_level = include_level
        self.include_module = include_module
        self.include_function = include_function
        self.include_line = include_line
        self.include_process = include_process
        self.include_thread = include_thread
        self.timestamp_format = timestamp_format
        self.extra_fields = extra_fields or {}

        # Get service metadata from environment
        self.service_name = os.getenv("SERVICE_NAME", "prep-api")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.version = os.getenv("APP_VERSION", "unknown")

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        log_entry: dict[str, Any] = {}

        # Timestamp
        if self.include_timestamp:
            if self.timestamp_format == "iso":
                log_entry["timestamp"] = datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).isoformat()
            elif self.timestamp_format == "epoch":
                log_entry["timestamp"] = record.created
            else:
                log_entry["timestamp"] = datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).strftime(self.timestamp_format)

        # Log level
        if self.include_level:
            log_entry["level"] = record.levelname
            log_entry["level_num"] = record.levelno

        # Logger name
        if self.include_logger:
            log_entry["logger"] = record.name

        # Source location
        if self.include_module:
            log_entry["module"] = record.module
        if self.include_function:
            log_entry["function"] = record.funcName
        if self.include_line:
            log_entry["line"] = record.lineno

        # Process/thread info
        if self.include_process:
            log_entry["process_id"] = record.process
            log_entry["process_name"] = record.processName
        if self.include_thread:
            log_entry["thread_id"] = record.thread
            log_entry["thread_name"] = record.threadName

        # Service metadata
        log_entry["service"] = self.service_name
        log_entry["environment"] = self.environment
        log_entry["version"] = self.version

        # Correlation ID from context
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Request context
        request_context = request_context_var.get()
        if request_context:
            log_entry["request"] = request_context

        # Message
        log_entry["message"] = record.getMessage()

        # Exception info
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": (
                    traceback.format_exception(*record.exc_info)
                    if record.exc_info[0]
                    else None
                ),
            }

        # Extra fields from record
        extra = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "taskName",
                "message",
            }
        }
        if extra:
            log_entry["extra"] = mask_sensitive_data(extra)

        # Static extra fields
        if self.extra_fields:
            log_entry.update(self.extra_fields)

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging with correlation IDs.

    Features:
    - Assigns unique correlation ID to each request
    - Logs request start and completion
    - Captures response time
    - Propagates correlation ID via response headers
    """

    def __init__(
        self,
        app,
        *,
        logger_name: str = "prep.http",
        log_request_body: bool = False,
        log_response_body: bool = False,
        excluded_paths: set[str] | None = None,
    ):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.excluded_paths = excluded_paths or {
            "/health",
            "/metrics",
            "/ready",
            "/live",
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with logging and correlation ID."""
        # Skip logging for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Generate or extract correlation ID
        correlation_id = (
            request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or str(uuid.uuid4())
        )

        # Set context variables
        correlation_id_var.set(correlation_id)
        request_context_var.set(
            {
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params) if request.query_params else None,
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("User-Agent"),
            }
        )

        # Log request start
        self.logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "event": "request_started",
                "http_method": request.method,
                "http_path": request.url.path,
            },
        )

        import time

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log request completion
            log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
            self.logger.log(
                log_level,
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "event": "request_completed",
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.exception(
                f"Request failed: {request.method} {request.url.path} - {type(e).__name__}",
                extra={
                    "event": "request_failed",
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error_type": type(e).__name__,
                },
            )
            raise
        finally:
            # Clear context
            correlation_id_var.set(None)
            request_context_var.set({})

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, considering proxies."""
        # Check X-Forwarded-For header (set by proxies/load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Return first IP in chain (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"


@lru_cache(maxsize=1)
def get_log_level() -> int:
    """Get configured log level from environment."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


@lru_cache(maxsize=1)
def is_json_logging_enabled() -> bool:
    """Check if JSON logging is enabled."""
    return os.getenv("LOG_FORMAT", "json").lower() == "json"


def configure_logging(
    *,
    level: int | None = None,
    json_format: bool | None = None,
    include_process: bool = False,
    include_thread: bool = False,
) -> None:
    """Configure application logging.

    Args:
        level: Log level (defaults to LOG_LEVEL env var or INFO)
        json_format: Use JSON formatting (defaults to LOG_FORMAT env var)
        include_process: Include process info in logs
        include_thread: Include thread info in logs
    """
    if level is None:
        level = get_log_level()

    if json_format is None:
        json_format = is_json_logging_enabled()

    # Create root handler
    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        formatter = JSONFormatter(
            include_process=include_process,
            include_thread=include_thread,
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)

    root_logger.addHandler(handler)

    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Application loggers at configured level
    logging.getLogger("prep").setLevel(level)
    logging.getLogger("api").setLevel(level)
    logging.getLogger("agents").setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Use this instead of logging.getLogger() to ensure consistent configuration.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Structured logging helpers
class StructuredLogger:
    """Helper class for structured logging with consistent extra fields.

    Usage:
        logger = StructuredLogger(__name__)
        logger.info("User logged in", user_id=123, method="oauth")
    """

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Log with structured extra fields."""
        self._logger.log(level, message, extra=mask_sensitive_data(kwargs))

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        self._logger.exception(message, extra=mask_sensitive_data(kwargs))


__all__ = [
    "JSONFormatter",
    "LoggingMiddleware",
    "StructuredLogger",
    "configure_logging",
    "correlation_id_var",
    "get_logger",
    "get_log_level",
    "is_json_logging_enabled",
    "mask_sensitive_data",
    "request_context_var",
]
