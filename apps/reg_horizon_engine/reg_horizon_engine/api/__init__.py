"""API namespace for the Regulatory Horizon Engine."""

from .routes.relationships import router as relationships_router

__all__ = ["relationships_router"]
