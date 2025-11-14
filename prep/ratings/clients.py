"""Async clients for external rating providers."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from .schemas import (
    ExternalBusiness,
    ExternalBusinessDetails,
    ExternalBusinessReview,
    ExternalBusinessSearchResponse,
    ExternalCategory,
    ExternalReviewListResponse,
)

logger = logging.getLogger(__name__)


class ExternalAPIError(RuntimeError):
    """Raised when an upstream ratings provider returns an error."""

    def __init__(self, provider: str, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class YelpAPIClient:
    """Minimal asynchronous wrapper around the Yelp Fusion API."""

    BASE_URL = "https://api.yelp.com/v3"
    SEARCH_PATH = "/businesses/search"
    BUSINESS_PATH = "/businesses/{business_id}"
    REVIEWS_PATH = "/businesses/{business_id}/reviews"

    def __init__(self, api_key: str | None = None, *, timeout: float = 10.0) -> None:
        self.api_key = api_key or os.getenv("YELP_API_KEY")
        self.timeout = timeout

    async def search_businesses(
        self,
        *,
        term: str,
        location: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        limit: int = 20,
    ) -> ExternalBusinessSearchResponse:
        if not self.api_key:
            raise ExternalAPIError("yelp", "Yelp API key not configured")

        params: dict[str, Any] = {"term": term, "limit": min(limit, 50)}
        if location:
            params["location"] = location
        if latitude is not None and longitude is not None:
            params["latitude"] = latitude
            params["longitude"] = longitude

        data = await self._request("GET", self.SEARCH_PATH, params=params)
        businesses = [self._to_business(item) for item in data.get("businesses", [])]
        total = int(data.get("total", len(businesses)))
        context = {"region": data.get("region", {})}
        return ExternalBusinessSearchResponse(businesses=businesses, total=total, context=context)

    async def get_business(self, business_id: str) -> ExternalBusinessDetails:
        if not self.api_key:
            raise ExternalAPIError("yelp", "Yelp API key not configured")

        path = self.BUSINESS_PATH.format(business_id=business_id)
        data = await self._request("GET", path)
        business = self._to_business(data)
        return ExternalBusinessDetails(
            **business.model_dump(),
            photos=list(data.get("photos", []) or []),
            hours={"hours": data.get("hours", [])},
            attributes=data.get("attributes", {}) or {},
        )

    async def get_reviews(self, business_id: str) -> ExternalReviewListResponse:
        if not self.api_key:
            raise ExternalAPIError("yelp", "Yelp API key not configured")

        path = self.REVIEWS_PATH.format(business_id=business_id)
        data = await self._request("GET", path)
        reviews = [self._to_review(item) for item in data.get("reviews", [])]
        return ExternalReviewListResponse(
            business_id=business_id,
            source="yelp",
            reviews=reviews,
            total=len(reviews),
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network failure path
            status = exc.response.status_code
            text = exc.response.text
            logger.warning(
                "Yelp API request failed", extra={"url": url, "status": status, "body": text}
            )
            raise ExternalAPIError("yelp", text or "Yelp API error", status_code=status) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - network failure path
            logger.warning("Yelp API request error", exc_info=exc, extra={"url": url})
            raise ExternalAPIError("yelp", "Failed to reach Yelp API") from exc

    def _to_business(self, data: dict[str, Any]) -> ExternalBusiness:
        categories = [
            ExternalCategory(alias=item.get("alias", ""), title=item.get("title", ""))
            for item in data.get("categories", [])
        ]
        location = data.get("location", {}) or {}
        coords = data.get("coordinates", {}) or {}
        address = [line for line in location.get("display_address", []) if line]
        return ExternalBusiness(
            id=str(data.get("id")),
            name=data.get("name", ""),
            source="yelp",
            url=data.get("url"),
            phone=data.get("display_phone"),
            address=address,
            city=location.get("city"),
            state=location.get("state"),
            postal_code=location.get("zip_code"),
            country=location.get("country"),
            latitude=coords.get("latitude"),
            longitude=coords.get("longitude"),
            rating=data.get("rating"),
            review_count=data.get("review_count"),
            price=data.get("price"),
            categories=categories,
            metadata={"id": data.get("id"), "alias": data.get("alias")},
        )

    def _to_review(self, data: dict[str, Any]) -> ExternalBusinessReview:
        user = data.get("user", {}) or {}
        return ExternalBusinessReview(
            id=str(data.get("id")),
            source="yelp",
            author=user.get("name"),
            rating=data.get("rating"),
            text=data.get("text"),
            language=data.get("language"),
            url=data.get("url"),
            created_at=data.get("time_created"),
            metadata={"user": user},
        )


class GooglePlacesClient:
    """Async client for the Google Places API."""

    SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

    def __init__(self, api_key: str | None = None, *, timeout: float = 10.0) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.timeout = timeout

    async def search_places(
        self,
        *,
        query: str,
        location: str | None = None,
        limit: int = 20,
    ) -> ExternalBusinessSearchResponse:
        if not self.api_key:
            raise ExternalAPIError("google", "Google Places API key not configured")

        params: dict[str, Any] = {"query": query, "key": self.api_key}
        if location:
            params["location"] = location
        params["radius"] = 40000

        data = await self._request(self.SEARCH_URL, params=params)
        results = data.get("results", [])
        businesses = [self._to_business(item) for item in results][:limit]
        total = int(data.get("total_results", len(results)))
        context = {"status": data.get("status"), "next_page_token": data.get("next_page_token")}
        return ExternalBusinessSearchResponse(businesses=businesses, total=total, context=context)

    async def get_place(self, place_id: str) -> ExternalBusinessDetails:
        if not self.api_key:
            raise ExternalAPIError("google", "Google Places API key not configured")

        params = {
            "place_id": place_id,
            "key": self.api_key,
            "fields": "place_id,name,formatted_address,geometry,types,url,formatted_phone_number,"
            "user_ratings_total,rating,price_level,opening_hours,website,photos",
        }
        data = await self._request(self.DETAILS_URL, params=params)
        result = data.get("result", {})
        business = self._to_business(result)
        photos = [
            photo.get("photo_reference")
            for photo in result.get("photos", [])
            if photo.get("photo_reference")
        ]
        details = ExternalBusinessDetails(
            **business.model_dump(),
            photos=photos,
            hours=result.get("opening_hours", {}),
            attributes={"website": result.get("website")},
        )
        return details

    async def get_reviews(self, place_id: str) -> ExternalReviewListResponse:
        if not self.api_key:
            raise ExternalAPIError("google", "Google Places API key not configured")

        params = {
            "place_id": place_id,
            "key": self.api_key,
            "fields": "reviews,place_id",
        }
        data = await self._request(self.DETAILS_URL, params=params)
        result = data.get("result", {})
        reviews = [self._to_review(item) for item in result.get("reviews", [])]
        return ExternalReviewListResponse(
            business_id=place_id,
            source="google",
            reviews=reviews,
            total=len(reviews),
        )

    async def _request(self, url: str, *, params: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network failure path
            status = exc.response.status_code
            text = exc.response.text
            logger.warning(
                "Google Places API request failed",
                extra={"url": url, "status": status, "body": text},
            )
            raise ExternalAPIError(
                "google", text or "Google Places API error", status_code=status
            ) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - network failure path
            logger.warning("Google Places API request error", exc_info=exc, extra={"url": url})
            raise ExternalAPIError("google", "Failed to reach Google Places API") from exc

        status = payload.get("status", "OK")
        if status not in {"OK", "ZERO_RESULTS"}:
            message = payload.get("error_message", f"Google Places error: {status}")
            raise ExternalAPIError("google", message)
        return payload

    def _to_business(self, data: dict[str, Any]) -> ExternalBusiness:
        geometry = data.get("geometry", {}) or {}
        location = geometry.get("location", {}) or {}
        categories = [
            ExternalCategory(alias=type_name, title=type_name.replace("_", " ").title())
            for type_name in data.get("types", [])
        ]
        rating = data.get("rating")
        if rating is not None:
            try:
                rating = float(rating)
            except (TypeError, ValueError):  # pragma: no cover - defensive parsing
                rating = None
        review_count = data.get("user_ratings_total")
        metadata = {
            "place_id": data.get("place_id"),
            "reference": data.get("reference"),
        }
        return ExternalBusiness(
            id=str(data.get("place_id")),
            name=data.get("name", ""),
            source="google",
            url=data.get("url") or data.get("website"),
            phone=data.get("formatted_phone_number"),
            address=[data.get("formatted_address", "")],
            city=None,
            state=None,
            postal_code=None,
            country=None,
            latitude=location.get("lat"),
            longitude=location.get("lng"),
            rating=rating,
            review_count=review_count,
            price=self._price_level_to_string(data.get("price_level")),
            categories=categories,
            metadata=metadata,
        )

    def _to_review(self, data: dict[str, Any]) -> ExternalBusinessReview:
        author = data.get("author_name")
        try:
            rating = float(data.get("rating")) if data.get("rating") is not None else None
        except (TypeError, ValueError):  # pragma: no cover - defensive parsing
            rating = None
        return ExternalBusinessReview(
            id=str(data.get("time")),
            source="google",
            author=author,
            rating=rating,
            text=data.get("text"),
            language=data.get("language"),
            url=data.get("author_url"),
            created_at=data.get("relative_time_description"),
            metadata={"profile_photo_url": data.get("profile_photo_url")},
        )

    def _price_level_to_string(self, price_level: Any) -> str | None:
        try:
            level = int(price_level)
        except (TypeError, ValueError):  # pragma: no cover - defensive parsing
            return None
        return "$" * max(level, 1)


__all__ = [
    "ExternalAPIError",
    "GooglePlacesClient",
    "YelpAPIClient",
]
