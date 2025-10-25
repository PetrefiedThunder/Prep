"""Domain services for the Prep smart matching engine."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.cache import RedisProtocol
from prep.models.orm import (
    Booking,
    BookingStatus,
    Kitchen,
    KitchenExternalRating,
    KitchenMatchingProfile,
    Review,
    ReviewStatus,
    User,
    UserMatchingPreference,
)

from .schemas import (
    ExternalRatingModel,
    ExternalRatingSyncRequest,
    ExternalRatingSyncResponse,
    KitchenMatchModel,
    KitchenMatchRequest,
    KitchenRatingResponse,
    MatchReason,
    MatchResponse,
    PreferenceSettings,
    UserPreferenceModel,
)


class MatchingService:
    """Coordinates matching algorithms, persistence and caching."""

    CACHE_TTL_SECONDS = 300

    WEIGHTS = {
        "equipment": 0.18,
        "certifications": 0.15,
        "cuisine": 0.12,
        "location": 0.14,
        "price": 0.12,
        "availability": 0.08,
        "popularity": 0.1,
        "rating": 0.11,
    }

    def __init__(self, session: AsyncSession, redis: RedisProtocol) -> None:
        self.session = session
        self.redis = redis

    # ------------------------------------------------------------------
    # Preference management
    # ------------------------------------------------------------------
    async def set_preferences(
        self, user: User, payload: PreferenceSettings
    ) -> UserPreferenceModel:
        """Persist matching preferences for a user."""

        normalized = self._normalize_preferences(payload)

        preference = await self.session.get(UserMatchingPreference, user.id)
        if preference is None:
            preference = UserMatchingPreference(user_id=user.id)
            self.session.add(preference)

        preference.equipment = normalized.equipment
        preference.certifications = normalized.certifications
        preference.cuisines = normalized.cuisines
        preference.preferred_cities = normalized.preferred_cities
        preference.preferred_states = normalized.preferred_states
        preference.availability = normalized.availability
        preference.min_price = normalized.min_price
        preference.max_price = normalized.max_price
        preference.max_distance_km = normalized.max_distance_km
        preference.preference_metadata = {
            "updated_by": str(user.id),
        }

        await self.session.commit()

        # Invalidate cached recommendations by expiring them immediately.
        await self._invalidate_cache(user.id)

        refreshed = await self.session.get(UserMatchingPreference, user.id)
        if refreshed is None:  # pragma: no cover - defensive guard
            raise HTTPException(status_code=500, detail="Failed to load preferences")

        return self._to_preference_model(refreshed)

    async def get_preferences(self, user_id: UUID) -> UserPreferenceModel | None:
        """Load stored preferences for a user if they exist."""

        preference = await self.session.get(UserMatchingPreference, user_id)
        if preference is None:
            return None
        return self._to_preference_model(preference)

    # ------------------------------------------------------------------
    # Matching logic
    # ------------------------------------------------------------------
    async def match_kitchens(
        self, user: User, request: KitchenMatchRequest
    ) -> MatchResponse:
        """Compute kitchen recommendations for the given user."""

        stored = await self.get_preferences(user.id)
        combined = self._merge_preferences(stored, request.preferences)
        response = await self._compute_matches(user, combined, request.limit)
        await self._cache_recommendations(user.id, response)
        return response

    async def get_recommendations(self, user_id: UUID) -> MatchResponse:
        """Return cached or freshly-computed recommendations for a user."""

        cached = await self.redis.get(self._cache_key(user_id))
        if isinstance(cached, str) and cached:
            try:
                payload = json.loads(cached)
                return MatchResponse.model_validate(payload)
            except ValueError:  # pragma: no cover - deserialization fallback
                pass

        user = await self.session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        preferences = await self.get_preferences(user_id)
        combined = self._merge_preferences(preferences, None)
        response = await self._compute_matches(user, combined, limit=10)
        await self._cache_recommendations(user_id, response)
        return response

    async def _compute_matches(
        self, user: User, preferences: PreferenceSettings, limit: int
    ) -> MatchResponse:
        """Evaluate all candidate kitchens against provided preferences."""

        stmt = (
            select(Kitchen, KitchenMatchingProfile)
            .join(KitchenMatchingProfile, KitchenMatchingProfile.kitchen_id == Kitchen.id, isouter=True)
            .where(Kitchen.published.is_(True))
            .where(Kitchen.moderation_status == "approved")
        )

        if preferences.preferred_cities:
            cities = [city.lower() for city in preferences.preferred_cities]
            stmt = stmt.where(func.lower(Kitchen.city).in_(cities))
        if preferences.preferred_states:
            states = [state.lower() for state in preferences.preferred_states]
            stmt = stmt.where(func.lower(Kitchen.state).in_(states))
        if preferences.max_price is not None:
            stmt = stmt.where(Kitchen.hourly_rate <= preferences.max_price)
        if preferences.min_price is not None:
            stmt = stmt.where(Kitchen.hourly_rate >= preferences.min_price)

        stmt = stmt.order_by(Kitchen.trust_score.desc().nullslast())

        result = await self.session.execute(stmt)
        candidates = result.all()
        if not candidates:
            return MatchResponse(matches=[], generated_at=datetime.now(UTC), preferences=preferences)

        kitchen_ids = [kitchen.id for kitchen, _ in candidates]
        metrics = await self._load_booking_metrics(kitchen_ids)
        rating_map = await self._load_rating_map(kitchen_ids)

        matches: list[KitchenMatchModel] = []
        for kitchen, profile in candidates:
            match = self._score_kitchen(
                kitchen,
                profile,
                preferences,
                metrics.get(kitchen.id, {}),
                rating_map.get(kitchen.id, {}),
            )
            matches.append(match)

        matches.sort(key=lambda item: item.confidence, reverse=True)
        trimmed = matches[:limit]
        return MatchResponse(
            matches=trimmed,
            generated_at=datetime.now(UTC),
            preferences=preferences,
        )

    # ------------------------------------------------------------------
    # External ratings
    # ------------------------------------------------------------------
    async def get_kitchen_ratings(self, kitchen_id: UUID) -> KitchenRatingResponse:
        """Aggregate internal and external rating sources for a kitchen."""

        review_stmt = (
            select(
                func.avg(Review.rating).label("avg_rating"),
                func.count(Review.id).label("total"),
            )
            .where(Review.kitchen_id == kitchen_id)
            .where(Review.status == ReviewStatus.APPROVED)
        )
        avg_rating, review_count = (await self.session.execute(review_stmt)).one()

        ratings_stmt = select(KitchenExternalRating).where(
            KitchenExternalRating.kitchen_id == kitchen_id
        )
        rows = (await self.session.execute(ratings_stmt)).scalars().all()

        external_sources: list[ExternalRatingModel] = []
        total_weight = float(review_count or 0)
        weighted_sum = (avg_rating or 0) * float(review_count or 0)

        for row in rows:
            normalized = row.normalized_rating
            if normalized is None:
                normalized = self._normalize_rating(row.rating, row.rating_scale)
                row.normalized_rating = normalized
            external_sources.append(
                ExternalRatingModel(
                    source=row.source,
                    rating=row.rating,
                    rating_scale=row.rating_scale,
                    rating_count=row.rating_count,
                    normalized_rating=normalized,
                    url=row.url,
                    synced_at=row.last_synced_at,
                    metadata=row.details or {},
                )
            )
            if row.rating_count:
                total_weight += row.rating_count
                weighted_sum += normalized * row.rating_count

        normalized_score = weighted_sum / total_weight if total_weight else None

        return KitchenRatingResponse(
            kitchen_id=kitchen_id,
            internal_average=float(avg_rating) if avg_rating is not None else None,
            internal_count=int(review_count or 0),
            external_sources=external_sources,
            normalized_score=normalized_score,
        )

    async def sync_external_ratings(
        self, payload: ExternalRatingSyncRequest
    ) -> ExternalRatingSyncResponse:
        """Upsert external ratings from Yelp/Google style integrations."""

        updated_sources: list[ExternalRatingModel] = []
        now = datetime.now(UTC)

        for entry in payload.sources:
            normalized_rating = self._normalize_rating(entry.rating, entry.rating_scale)
            stmt = select(KitchenExternalRating).where(
                and_(
                    KitchenExternalRating.kitchen_id == entry.kitchen_id,
                    KitchenExternalRating.source == entry.source,
                )
            )
            existing = (await self.session.execute(stmt)).scalar_one_or_none()

            if existing:
                existing.rating = entry.rating
                existing.rating_scale = entry.rating_scale
                existing.rating_count = entry.rating_count
                existing.normalized_rating = normalized_rating
                existing.url = str(entry.url) if entry.url else None
                existing.details = entry.metadata
                existing.last_synced_at = now
                record = existing
            else:
                record = KitchenExternalRating(
                    kitchen_id=entry.kitchen_id,
                    source=entry.source,
                    rating=entry.rating,
                    rating_scale=entry.rating_scale,
                    rating_count=entry.rating_count,
                    normalized_rating=normalized_rating,
                    url=str(entry.url) if entry.url else None,
                    details=entry.metadata,
                    last_synced_at=now,
                )
                self.session.add(record)

            updated_sources.append(
                ExternalRatingModel(
                    source=record.source,
                    rating=record.rating,
                    rating_scale=record.rating_scale,
                    rating_count=record.rating_count,
                    normalized_rating=record.normalized_rating,
                    url=record.url,
                    synced_at=record.last_synced_at,
                    metadata=record.details or {},
                )
            )

        await self.session.commit()

        return ExternalRatingSyncResponse(updated=len(updated_sources), sources=updated_sources)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _normalize_preferences(self, payload: PreferenceSettings) -> PreferenceSettings:
        """Return a copy with canonical casing and ordering."""

        def normalize_list(items: list[str]) -> list[str]:
            normalized_items = {item.strip().lower() for item in items if item.strip()}
            return sorted(normalized_items)

        return PreferenceSettings(
            equipment=normalize_list(payload.equipment),
            certifications=normalize_list(payload.certifications),
            cuisines=normalize_list(payload.cuisines),
            preferred_cities=normalize_list(payload.preferred_cities),
            preferred_states=normalize_list(payload.preferred_states),
            availability=normalize_list(payload.availability),
            min_price=payload.min_price,
            max_price=payload.max_price,
            max_distance_km=payload.max_distance_km,
        )

    def _merge_preferences(
        self,
        stored: UserPreferenceModel | None,
        override: PreferenceSettings | None,
    ) -> PreferenceSettings:
        """Combine persisted preferences with request overrides."""

        stored_payload = PreferenceSettings(**stored.model_dump()) if stored else PreferenceSettings()
        if override is None:
            return stored_payload

        merged = stored_payload.model_copy(update=override.model_dump(exclude_unset=True))
        return self._normalize_preferences(merged)

    async def _cache_recommendations(self, user_id: UUID, response: MatchResponse) -> None:
        """Persist the recommendation payload to Redis."""

        payload = json.dumps(response.model_dump(), default=self._json_serializer)
        await self.redis.setex(self._cache_key(user_id), self.CACHE_TTL_SECONDS, payload)

    async def _invalidate_cache(self, user_id: UUID) -> None:
        """Expire cached recommendations for a user."""

        await self.redis.setex(self._cache_key(user_id), 1, "")

    def _cache_key(self, user_id: UUID) -> str:
        return f"match:users:{user_id}"

    def _to_preference_model(self, preference: UserMatchingPreference) -> UserPreferenceModel:
        return UserPreferenceModel(
            user_id=preference.user_id,
            equipment=preference.equipment or [],
            certifications=preference.certifications or [],
            cuisines=preference.cuisines or [],
            preferred_cities=preference.preferred_cities or [],
            preferred_states=preference.preferred_states or [],
            availability=preference.availability or [],
            min_price=preference.min_price,
            max_price=preference.max_price,
            max_distance_km=preference.max_distance_km,
            updated_at=preference.updated_at,
        )

    async def _load_booking_metrics(self, kitchen_ids: list[UUID]) -> dict[UUID, dict[str, Any]]:
        if not kitchen_ids:
            return {}

        window = datetime.now(UTC) - timedelta(days=30)
        stmt = (
            select(
                Booking.kitchen_id,
                func.count(Booking.id).label("total"),
                func.count(func.distinct(Booking.customer_id)).label("unique_customers"),
                func.sum(
                    case((Booking.start_time >= window, 1), else_=0)
                ).label("recent"),
            )
            .where(Booking.kitchen_id.in_(kitchen_ids))
            .where(Booking.status == BookingStatus.COMPLETED)
            .group_by(Booking.kitchen_id)
        )
        rows = await self.session.execute(stmt)
        metrics: dict[UUID, dict[str, Any]] = defaultdict(dict)
        for row in rows:
            metrics[row.kitchen_id] = {
                "total": int(row.total or 0),
                "unique_customers": int(row.unique_customers or 0),
                "recent": int(row.recent or 0),
            }
        return metrics

    async def _load_rating_map(self, kitchen_ids: list[UUID]) -> dict[UUID, dict[str, Any]]:
        if not kitchen_ids:
            return {}

        review_stmt = (
            select(
                Review.kitchen_id,
                func.avg(Review.rating).label("avg_rating"),
                func.count(Review.id).label("count"),
            )
            .where(Review.kitchen_id.in_(kitchen_ids))
            .where(Review.status == ReviewStatus.APPROVED)
            .group_by(Review.kitchen_id)
        )
        review_rows = await self.session.execute(review_stmt)
        rating_map: dict[UUID, dict[str, Any]] = defaultdict(dict)
        for row in review_rows:
            rating_map[row.kitchen_id].update(
                {
                    "internal_avg": float(row.avg_rating) if row.avg_rating is not None else None,
                    "internal_count": int(row.count or 0),
                }
            )

        external_stmt = select(KitchenExternalRating).where(
            KitchenExternalRating.kitchen_id.in_(kitchen_ids)
        )
        for rating in (await self.session.execute(external_stmt)).scalars():
            bucket = rating_map[rating.kitchen_id]
            external = bucket.setdefault("external", [])
            external.append(rating)

        return rating_map

    def _score_kitchen(
        self,
        kitchen: Kitchen,
        profile: KitchenMatchingProfile | None,
        preferences: PreferenceSettings,
        metrics: dict[str, Any],
        rating_info: dict[str, Any],
    ) -> KitchenMatchModel:
        weight_total = 0.0
        score_total = 0.0
        reasons: list[MatchReason] = []

        profile_equipment = set((profile.equipment if profile else []) or [])
        requested_equipment = set(preferences.equipment or [])
        if requested_equipment:
            weight = self.WEIGHTS["equipment"]
            weight_total += weight
            overlap = requested_equipment & {item.lower() for item in profile_equipment}
            ratio = len(overlap) / len(requested_equipment)
            contribution = ratio * weight
            score_total += contribution
            reasons.append(
                MatchReason(
                    criterion="equipment",
                    summary=f"Matches {len(overlap)} of {len(requested_equipment)} required equipment",
                    weight=weight,
                    contribution=contribution,
                )
            )

        requested_certifications = set(preferences.certifications or [])
        profile_certifications = set((profile.certifications if profile else []) or [])
        if requested_certifications:
            weight = self.WEIGHTS["certifications"]
            weight_total += weight
            overlap = requested_certifications & {item.lower() for item in profile_certifications}
            ratio = len(overlap) / len(requested_certifications)
            contribution = ratio * weight
            score_total += contribution
            reasons.append(
                MatchReason(
                    criterion="certifications",
                    summary=f"Supports {len(overlap)} of {len(requested_certifications)} certification requirements",
                    weight=weight,
                    contribution=contribution,
                )
            )

        requested_cuisines = set(preferences.cuisines or [])
        profile_cuisines = set((profile.cuisines if profile else []) or [])
        if requested_cuisines:
            weight = self.WEIGHTS["cuisine"]
            weight_total += weight
            overlap = requested_cuisines & {item.lower() for item in profile_cuisines}
            ratio = len(overlap) / len(requested_cuisines)
            contribution = ratio * weight
            score_total += contribution
            reasons.append(
                MatchReason(
                    criterion="cuisine",
                    summary=f"Cuisine affinity {len(overlap)}/{len(requested_cuisines)}",
                    weight=weight,
                    contribution=contribution,
                )
            )

        if preferences.preferred_cities or preferences.preferred_states:
            weight = self.WEIGHTS["location"]
            weight_total += weight
            city_match = 0.0
            if preferences.preferred_cities and kitchen.city:
                city_match = 1.0 if kitchen.city.lower() in preferences.preferred_cities else 0.0
            state_match = 0.0
            if preferences.preferred_states and kitchen.state:
                state_match = 0.7 if kitchen.state.lower() in preferences.preferred_states else 0.0
            ratio = max(city_match, state_match)
            contribution = ratio * weight
            score_total += contribution
            reasons.append(
                MatchReason(
                    criterion="location",
                    summary="Preferred location alignment" if ratio else "Outside preferred markets",
                    weight=weight,
                    contribution=contribution,
                )
            )

        if preferences.max_price is not None or preferences.min_price is not None:
            weight = self.WEIGHTS["price"]
            weight_total += weight
            price = float(kitchen.hourly_rate) if kitchen.hourly_rate is not None else None
            if price is None:
                ratio = 0.0
            else:
                within_min = preferences.min_price is None or price >= preferences.min_price
                within_max = preferences.max_price is None or price <= preferences.max_price
                ratio = 1.0 if within_min and within_max else 0.0
            contribution = ratio * weight
            score_total += contribution
            reasons.append(
                MatchReason(
                    criterion="price",
                    summary="Within preferred price range" if ratio else "Outside preferred price range",
                    weight=weight,
                    contribution=contribution,
                )
            )

        requested_availability = set(preferences.availability or [])
        profile_availability = set((profile.availability if profile else []) or [])
        if requested_availability:
            weight = self.WEIGHTS["availability"]
            weight_total += weight
            overlap = requested_availability & {item.lower() for item in profile_availability}
            ratio = len(overlap) / len(requested_availability)
            contribution = ratio * weight
            score_total += contribution
            reasons.append(
                MatchReason(
                    criterion="availability",
                    summary=f"Availability overlap {len(overlap)}/{len(requested_availability)}",
                    weight=weight,
                    contribution=contribution,
                )
            )

        popularity_weight = self.WEIGHTS["popularity"]
        weight_total += popularity_weight
        total_bookings = metrics.get("total", 0)
        recent_bookings = metrics.get("recent", 0)
        popularity_score = min(total_bookings / 10, 1.0)
        score_total += popularity_score * popularity_weight
        reasons.append(
            MatchReason(
                criterion="popularity",
                summary=f"{total_bookings} lifetime bookings, {recent_bookings} in last 30 days",
                weight=popularity_weight,
                contribution=popularity_score * popularity_weight,
            )
        )

        rating_weight = self.WEIGHTS["rating"]
        weight_total += rating_weight
        normalized_rating = rating_info.get("normalized")
        if normalized_rating is None:
            normalized_rating = self._calculate_normalized_rating(rating_info)
        rating_score = (normalized_rating / 5) if normalized_rating else 0.0
        score_total += rating_score * rating_weight
        reasons.append(
            MatchReason(
                criterion="rating",
                summary="High customer satisfaction" if rating_score else "Insufficient rating data",
                weight=rating_weight,
                contribution=rating_score * rating_weight,
            )
        )

        confidence = score_total / weight_total if weight_total else 0.0
        confidence = max(0.0, min(confidence, 1.0))

        external_rating = normalized_rating
        demand_forecast = min(recent_bookings / 5, 1.0) if recent_bookings else 0.0

        return KitchenMatchModel(
            kitchen_id=kitchen.id,
            kitchen_name=kitchen.name,
            city=kitchen.city,
            state=kitchen.state,
            hourly_rate=float(kitchen.hourly_rate) if kitchen.hourly_rate is not None else None,
            trust_score=kitchen.trust_score,
            score=confidence,
            confidence=confidence,
            reasons=reasons,
            cuisines=[*(profile.cuisines if profile and profile.cuisines else [])],
            equipment=[*(profile.equipment if profile and profile.equipment else [])],
            certifications=[*(profile.certifications if profile and profile.certifications else [])],
            availability=[*(profile.availability if profile and profile.availability else [])],
            external_rating=external_rating,
            popularity_index=popularity_score,
            demand_forecast=demand_forecast,
        )

    def _calculate_normalized_rating(self, rating_info: dict[str, Any]) -> float | None:
        internal_avg = rating_info.get("internal_avg")
        internal_count = rating_info.get("internal_count", 0)
        external_sources: list[KitchenExternalRating] = rating_info.get("external", [])

        total_weight = float(internal_count or 0)
        weighted_sum = (internal_avg or 0) * float(internal_count or 0)

        for source in external_sources:
            normalized = source.normalized_rating
            if normalized is None:
                normalized = self._normalize_rating(source.rating, source.rating_scale)
            count = source.rating_count or 0
            total_weight += count
            weighted_sum += normalized * count

        if total_weight == 0:
            return internal_avg

        return weighted_sum / total_weight if total_weight else internal_avg

    def _normalize_rating(self, rating: float, scale: float) -> float:
        if scale <= 0:  # pragma: no cover - guard
            return rating
        return min(max(rating / scale * 5, 0), 5)

    @staticmethod
    def _json_serializer(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        raise TypeError(f"Unsupported type for JSON serialization: {type(value)!r}")


__all__ = ["MatchingService"]
