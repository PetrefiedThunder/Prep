"""External ratings integration package."""

from .api import get_rating_service, router
from .service import RatingIntegrationService

__all__ = ["router", "get_rating_service", "RatingIntegrationService"]
