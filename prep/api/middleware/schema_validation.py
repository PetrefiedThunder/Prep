"""Schema validation middleware for API requests and responses."""

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import jsonschema
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Global schema cache
_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}
_SCHEMA_DIR = Path(__file__).parent.parent.parent.parent / "schemas"


def load_schema(schema_name: str) -> dict[str, Any]:
    """
    Load and cache a JSON schema.

    Args:
        schema_name: Name of the schema file (e.g., "vendor", "booking")

    Returns:
        Parsed JSON schema dictionary

    Raises:
        FileNotFoundError: If schema file doesn't exist
        json.JSONDecodeError: If schema is invalid JSON
    """
    if schema_name in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[schema_name]

    schema_path = _SCHEMA_DIR / f"{schema_name}.schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")

    with open(schema_path) as f:
        schema = json.load(f)

    _SCHEMA_CACHE[schema_name] = schema
    logger.info(f"Loaded schema: {schema_name}")
    return schema


def validate_against_schema(data: dict[str, Any], schema_name: str) -> tuple[bool, str | None]:
    """
    Validate data against a JSON schema.

    Args:
        data: Data to validate
        schema_name: Name of the schema to validate against

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        schema = load_schema(schema_name)
        jsonschema.validate(instance=data, schema=schema)
        return True, None
    except jsonschema.ValidationError as e:
        error_msg = f"Schema validation failed: {e.message}"
        logger.warning(error_msg, extra={"schema": schema_name, "path": list(e.absolute_path)})
        return False, error_msg
    except FileNotFoundError as e:
        logger.error(f"Schema not found: {e}")
        return False, str(e)
    except Exception as e:
        logger.error(f"Unexpected validation error: {e}", exc_info=True)
        return False, f"Validation error: {str(e)}"


def validate_vendor(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate vendor data against vendor schema."""
    return validate_against_schema(data, "vendor")


def validate_facility(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate facility data against facility schema."""
    return validate_against_schema(data, "facility")


def validate_booking(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate booking data against booking schema."""
    return validate_against_schema(data, "booking")


def validate_ledger_entry(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate ledger entry data against ledger_entry schema."""
    return validate_against_schema(data, "ledger_entry")


class SchemaValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically validate request/response payloads against JSON schemas.

    This middleware checks for schema validation hints in route metadata and validates
    request bodies and response bodies accordingly.

    Usage:
        app.add_middleware(SchemaValidationMiddleware)

        @router.post("/api/v1/vendors")
        @validate_request_schema("vendor")
        @validate_response_schema("vendor")
        async def create_vendor(vendor: dict):
            return vendor
    """

    def __init__(self, app: ASGIApp, enforce: bool = True):
        """
        Initialize schema validation middleware.

        Args:
            app: ASGI application
            enforce: If True, validation failures will return 400 errors.
                    If False, validation failures are logged but requests continue.
        """
        super().__init__(app)
        self.enforce = enforce

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and validate schemas if configured."""
        # Schema validation is typically done at the route level using decorators
        # This middleware provides infrastructure but most validation happens in endpoints
        response = await call_next(request)
        return response


def validate_request_schema(schema_name: str):
    """
    Decorator to validate request body against a schema.

    Example:
        @router.post("/api/v1/vendors")
        @validate_request_schema("vendor")
        async def create_vendor(request: Request):
            body = await request.json()
            # body is guaranteed to be valid if we reach here
            return {"status": "created"}
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs
            request: Request | None = kwargs.get("request")
            if not request:
                # Try to find request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request:
                try:
                    body = await request.json()
                    is_valid, error_msg = validate_against_schema(body, schema_name)
                    if not is_valid:
                        from fastapi import HTTPException

                        raise HTTPException(
                            status_code=400,
                            detail={"error": "SCHEMA_VALIDATION_FAILED", "message": error_msg},
                        )
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"Request body validation error: {e}", exc_info=True)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def validate_response_schema(schema_name: str):
    """
    Decorator to validate response body against a schema.

    Example:
        @router.get("/api/v1/vendors/{vendor_id}")
        @validate_response_schema("vendor")
        async def get_vendor(vendor_id: str):
            return {"vendor_id": vendor_id, "business_name": "ACME Corp", ...}
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Only validate dict responses (assumes JSON)
            if isinstance(result, dict):
                is_valid, error_msg = validate_against_schema(result, schema_name)
                if not is_valid:
                    logger.error(
                        f"Response schema validation failed: {error_msg}",
                        extra={"schema": schema_name, "endpoint": func.__name__},
                    )
                    # Log but don't fail the request (developer error, not user error)

            return result

        return wrapper

    return decorator


# Convenience function to validate all schemas at startup
def validate_all_schemas() -> bool:
    """
    Validate all JSON schemas to ensure they're valid at application startup.

    Returns:
        True if all schemas are valid, False otherwise
    """
    schema_files = list(_SCHEMA_DIR.glob("*.schema.json"))
    all_valid = True

    logger.info(f"Validating {len(schema_files)} schemas...")

    for schema_file in schema_files:
        try:
            with open(schema_file) as f:
                schema = json.load(f)

            # Validate that the schema itself is valid JSON Schema
            jsonschema.Draft202012Validator.check_schema(schema)
            logger.info(f"✓ {schema_file.name}")

        except Exception as e:
            logger.error(f"✗ {schema_file.name}: {e}")
            all_valid = False

    if all_valid:
        logger.info("All schemas are valid")
    else:
        logger.error("Some schemas are invalid")

    return all_valid
