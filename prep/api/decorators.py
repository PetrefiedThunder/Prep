"""API classification decorators for versioning and stability guarantees."""

import functools
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from fastapi import Header, HTTPException, Request, Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class APIStability(str, Enum):
    """API stability levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    EXPERIMENTAL = "experimental"


class APIMetadata(BaseModel):
    """Metadata about an API endpoint."""

    stability: APIStability
    version: str
    since: Optional[str] = None
    deprecated: bool = False
    sunset_date: Optional[str] = None
    service: Optional[str] = None
    feature: Optional[str] = None


# Global registry of API endpoints with their metadata
API_REGISTRY: dict[str, APIMetadata] = {}


def public_api(
    version: str,
    since: str,
    deprecated: bool = False,
    sunset_date: Optional[str] = None,
):
    """
    Decorator for Public APIs.

    Public APIs have strict backward compatibility guarantees and versioning.

    Args:
        version: API version (e.g., "v1", "v2")
        since: Date when this API was introduced (ISO format: YYYY-MM-DD)
        deprecated: Whether this API is deprecated
        sunset_date: Date when this API will be removed (ISO format: YYYY-MM-DD)

    Example:
        @public_api(version="v1", since="2025-01-01")
        @router.get("/api/v1/properties/{property_id}")
        async def get_property(property_id: str):
            pass
    """

    def decorator(func: Callable) -> Callable:
        # Register API metadata
        endpoint_name = f"{func.__module__}.{func.__name__}"
        API_REGISTRY[endpoint_name] = APIMetadata(
            stability=APIStability.PUBLIC,
            version=version,
            since=since,
            deprecated=deprecated,
            sunset_date=sunset_date,
        )

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Add API metadata headers to response
            response: Optional[Response] = kwargs.get("response")

            # Check if API is sunsetted
            if sunset_date:
                sunset_dt = datetime.fromisoformat(sunset_date)
                if datetime.now() >= sunset_dt:
                    logger.warning(
                        f"Sunsetted API called: {endpoint_name} (sunset: {sunset_date})"
                    )
                    raise HTTPException(
                        status_code=410,
                        detail={
                            "error": "API_SUNSETTED",
                            "message": f"This API was removed on {sunset_date}",
                            "migration_guide": f"/docs/migrations/{version}",
                        },
                    )

            # Execute the endpoint
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

            # Add headers if response object is available
            if response:
                response.headers["X-API-Stability"] = "public"
                response.headers["X-API-Version"] = version
                if deprecated:
                    response.headers["X-API-Deprecated"] = "true"
                    if sunset_date:
                        response.headers["X-API-Sunset"] = sunset_date
                        response.headers["Link"] = f'</docs/migrations/{version}>; rel="deprecation"'

            # Log usage for metrics
            logger.info(
                f"Public API called: {endpoint_name}",
                extra={
                    "api_version": version,
                    "deprecated": deprecated,
                    "stability": "public",
                },
            )

            return result

        # Store metadata on the function for OpenAPI generation
        wrapper._api_metadata = API_REGISTRY[endpoint_name]  # type: ignore
        return wrapper

    return decorator


def internal_service_api(service: str, version: str = "v1"):
    """
    Decorator for Internal Service APIs.

    Internal APIs are used for service-to-service communication.
    They have relaxed backward compatibility compared to public APIs.

    Args:
        service: Name of the calling service (e.g., "compliance-engine")
        version: API version (default: "v1")

    Example:
        @internal_service_api(service="compliance-engine")
        @router.post("/internal/v1/evaluate-rules")
        async def evaluate_rules():
            pass
    """

    def decorator(func: Callable) -> Callable:
        # Register API metadata
        endpoint_name = f"{func.__module__}.{func.__name__}"
        API_REGISTRY[endpoint_name] = APIMetadata(
            stability=APIStability.INTERNAL,
            version=version,
            service=service,
        )

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            response: Optional[Response] = kwargs.get("response")

            # Execute the endpoint
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

            # Add headers
            if response:
                response.headers["X-API-Stability"] = "internal"
                response.headers["X-API-Service"] = service
                response.headers["X-API-Version"] = version

            # Log usage
            logger.info(
                f"Internal API called: {endpoint_name}",
                extra={
                    "service": service,
                    "api_version": version,
                    "stability": "internal",
                },
            )

            return result

        wrapper._api_metadata = API_REGISTRY[endpoint_name]  # type: ignore
        return wrapper

    return decorator


def experimental_api(feature: str):
    """
    Decorator for Experimental APIs.

    Experimental APIs have ZERO backward compatibility guarantees.
    They can be changed or removed without notice.

    Args:
        feature: Name of the experimental feature (e.g., "ai-recommendations")

    Example:
        @experimental_api(feature="ai-compliance-copilot")
        @router.get("/experimental/v1/copilot/suggest")
        async def ai_suggest(x_experimental_api: str = Header(None)):
            pass
    """

    def decorator(func: Callable) -> Callable:
        # Register API metadata
        endpoint_name = f"{func.__module__}.{func.__name__}"
        API_REGISTRY[endpoint_name] = APIMetadata(
            stability=APIStability.EXPERIMENTAL,
            version="experimental",
            feature=feature,
        )

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Require explicit opt-in via header
            request: Optional[Request] = kwargs.get("request")
            x_experimental_api = None

            if request:
                x_experimental_api = request.headers.get("X-Experimental-API")

            if x_experimental_api != "true":
                logger.warning(
                    f"Experimental API called without opt-in header: {endpoint_name}"
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "EXPERIMENTAL_API_OPT_IN_REQUIRED",
                        "message": "This is an experimental API. You must include 'X-Experimental-API: true' header to use it.",
                        "feature": feature,
                    },
                )

            response: Optional[Response] = kwargs.get("response")

            # Execute the endpoint
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

            # Add warning headers
            if response:
                response.headers["X-API-Stability"] = "experimental"
                response.headers["X-API-Warning"] = "This API may change or be removed without notice"
                response.headers["X-API-Feature"] = feature

            # Log usage
            logger.warning(
                f"Experimental API called: {endpoint_name}",
                extra={
                    "feature": feature,
                    "stability": "experimental",
                },
            )

            return result

        wrapper._api_metadata = API_REGISTRY[endpoint_name]  # type: ignore
        return wrapper

    return decorator


def get_api_registry() -> dict[str, APIMetadata]:
    """Get the global API registry for OpenAPI spec generation."""
    return API_REGISTRY


def get_api_metadata(func: Callable) -> Optional[APIMetadata]:
    """Get API metadata from a decorated function."""
    return getattr(func, "_api_metadata", None)


# Import asyncio at the bottom to avoid circular imports
import asyncio
