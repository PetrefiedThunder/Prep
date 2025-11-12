"""Domain service implementing the native mobile API foundation."""

from __future__ import annotations

import base64
import json
import math
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.cache import RedisProtocol
from prep.matching.schemas import KitchenMatchModel
from prep.matching.service import MatchingService
from prep.models.orm import (
    Booking,
    BookingStatus,
    Kitchen,
    KitchenMatchingProfile,
    User,
    UserMatchingPreference,
)
from prep.ratings.service import RatingIntegrationService

from .schemas import (
    BandwidthEstimateResponse,
    BiometricRegistrationRequest,
    BiometricRegistrationResponse,
    BiometricStatusResponse,
    BiometricVerificationRequest,
    BiometricVerificationResponse,
    CacheStatusResponse,
    CameraUploadRequest,
    CameraUploadResponse,
    MobileAuthTokens,
    MobileBookingSummary,
    MobileKitchenDetailResponse,
    MobileKitchenSummary,
    MobileLoginRequest,
    MobileLoginResponse,
    MobileNearbyKitchensResponse,
    MobileUpcomingBookingsResponse,
    NotificationRegistrationRequest,
    NotificationRegistrationResponse,
    OfflineSyncResponse,
    OfflineUploadRequest,
    OfflineUploadResponse,
    PerformanceMetricsResponse,
    PerformanceReportRequest,
    PerformanceReportResponse,
    QuickBookingRequest,
    QuickBookingResponse,
    QuickSearchFilters,
    QuickSearchResponse,
)


class MobileGatewayService:
    """Coordinator responsible for the mobile native app surface area."""

    PUSH_REGISTRATION_TTL = 60 * 60 * 24 * 30  # 30 days
    SESSION_CACHE_TTL = 60 * 60 * 6  # 6 hours
    OFFLINE_CACHE_TTL = 60 * 60 * 12
    PERFORMANCE_TTL = 60 * 60 * 24
    BACKGROUND_SYNC_MINUTES_DEFAULT = 120

    def __init__(
        self,
        session: AsyncSession,
        redis: RedisProtocol,
        matching_service: MatchingService | None = None,
        rating_service: RatingIntegrationService | None = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.matching_service = matching_service or MatchingService(session, redis)
        self.rating_service = rating_service or RatingIntegrationService(session, redis)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    async def login(self, payload: MobileLoginRequest) -> MobileLoginResponse:
        stmt = select(User).where(func.lower(User.email) == payload.email.lower())
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None or not secrets.compare_digest(user.hashed_password or "", payload.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        if not user.is_active or user.is_suspended:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

        user.last_login_at = datetime.now(UTC)
        await self.session.commit()

        tokens = self._issue_tokens(user)
        await self._cache_session(
            user.id, payload.device.device_id, tokens, payload.device.app_version
        )

        interval = await self._get_background_interval(user.id)

        return MobileLoginResponse(
            user_id=user.id,
            tokens=tokens,
            features=[
                "offline-sync",
                "push-notifications",
                "quick-booking",
                "biometric-auth",
                "performance-metrics",
            ],
            background_sync_interval_minutes=interval,
        )

    def _issue_tokens(self, user: User) -> MobileAuthTokens:
        expires_in = 60 * 60
        payload = {
            "sub": str(user.id),
            "roles": ["mobile-user"],
            "exp": int((datetime.now(UTC) + timedelta(seconds=expires_in)).timestamp()),
        }
        token = self._encode_jwt(payload)
        refresh_payload = {
            "sub": str(user.id),
            "type": "refresh",
            "exp": int((datetime.now(UTC) + timedelta(days=7)).timestamp()),
        }
        refresh_token = self._encode_jwt(refresh_payload)
        return MobileAuthTokens(
            access_token=token, refresh_token=refresh_token, expires_in=expires_in
        )

    def _encode_jwt(self, payload: dict[str, Any]) -> str:
        header = {"alg": "none", "typ": "JWT"}
        header_segment = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=")
        payload_segment = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
        signature_segment = base64.urlsafe_b64encode(b"mobile").rstrip(b"=")
        return f"{header_segment.decode()}.{payload_segment.decode()}.{signature_segment.decode()}"

    async def _cache_session(
        self,
        user_id: UUID,
        device_id: str,
        tokens: MobileAuthTokens,
        app_version: str | None,
    ) -> None:
        key = self._session_cache_key(user_id, device_id)
        payload = {
            "user_id": str(user_id),
            "device_id": device_id,
            "app_version": app_version,
            "issued_at": datetime.now(UTC).isoformat(),
            "access_token": tokens.access_token,
        }
        await self.redis.setex(key, self.SESSION_CACHE_TTL, json.dumps(payload))

    def _session_cache_key(self, user_id: UUID, device_id: str) -> str:
        return f"mobile:session:{user_id}:{device_id}"

    # ------------------------------------------------------------------
    # Kitchen discovery
    # ------------------------------------------------------------------
    async def nearby_kitchens(
        self,
        user: User,
        *,
        latitude: float,
        longitude: float,
        radius_km: float,
        limit: int,
    ) -> MobileNearbyKitchensResponse:
        cache_key = f"mobile:nearby:{user.id}:{round(latitude, 2)}:{round(longitude, 2)}:{round(radius_km, 1)}:{limit}"
        cached = await self.redis.get(cache_key)
        if isinstance(cached, str):
            try:
                data = json.loads(cached)
                return MobileNearbyKitchensResponse.model_validate(data)
            except ValueError:
                pass

        stmt = (
            select(Kitchen, KitchenMatchingProfile)
            .join(
                KitchenMatchingProfile,
                KitchenMatchingProfile.kitchen_id == Kitchen.id,
                isouter=True,
            )
            .where(Kitchen.published.is_(True))
            .where(Kitchen.moderation_status == "approved")
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        summaries: list[MobileKitchenSummary] = []
        kitchen_ids: list[UUID] = []
        for kitchen, profile in rows:
            if not profile or profile.latitude is None or profile.longitude is None:
                continue
            distance = self._haversine(latitude, longitude, profile.latitude, profile.longitude)
            if distance > radius_km:
                continue
            kitchen_ids.append(kitchen.id)
            summaries.append(
                MobileKitchenSummary(
                    kitchen_id=kitchen.id,
                    name=kitchen.name,
                    distance_km=round(distance, 2),
                    city=kitchen.city,
                    state=kitchen.state,
                    hourly_rate=float(kitchen.hourly_rate)
                    if kitchen.hourly_rate is not None
                    else None,
                    trust_score=float(kitchen.trust_score)
                    if kitchen.trust_score is not None
                    else None,
                    normalized_rating=None,
                    rating_count=0,
                )
            )

        rating_map = await self.rating_service.get_rating_map(kitchen_ids)
        for summary in summaries:
            rating = rating_map.get(summary.kitchen_id)
            if rating:
                summary.normalized_rating = rating.normalized_score
                summary.rating_count = rating.external_count + rating.internal_count

        summaries.sort(key=lambda item: (item.distance_km or 9999, -(item.trust_score or 0)))
        summaries = summaries[:limit]

        response = MobileNearbyKitchensResponse(
            items=summaries,
            cached=False,
            generated_at=datetime.now(UTC),
        )
        await self.redis.setex(cache_key, self.SESSION_CACHE_TTL, response.model_dump_json())
        return response

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius = 6371.0
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius * c

    # ------------------------------------------------------------------
    # Bookings
    # ------------------------------------------------------------------
    async def upcoming_bookings(self, user: User) -> MobileUpcomingBookingsResponse:
        now = datetime.now(UTC)
        stmt = (
            select(Booking, Kitchen)
            .join(Kitchen, Kitchen.id == Booking.kitchen_id)
            .where(or_(Booking.customer_id == user.id, Booking.host_id == user.id))
            .where(Booking.end_time >= now)
            .where(Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING]))
            .order_by(Booking.start_time.asc())
        )
        result = await self.session.execute(stmt)
        items: list[MobileBookingSummary] = []
        for booking, kitchen in result.all():
            role = "host" if booking.host_id == user.id else "customer"
            items.append(
                MobileBookingSummary(
                    booking_id=booking.id,
                    kitchen_id=kitchen.id,
                    kitchen_name=kitchen.name,
                    status=booking.status.value,
                    start_time=booking.start_time,
                    end_time=booking.end_time,
                    role=role,
                )
            )
        return MobileUpcomingBookingsResponse(items=items, generated_at=datetime.now(UTC))

    async def quick_book(
        self,
        user: User,
        payload: QuickBookingRequest,
    ) -> QuickBookingResponse:
        if payload.end_time <= payload.start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid time range"
            )

        kitchen = await self.session.get(Kitchen, payload.kitchen_id)
        if kitchen is None or not kitchen.published:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not available"
            )

        total_amount = float(kitchen.hourly_rate or 0)
        platform_fee = round(total_amount * 0.1, 2) if total_amount else 0
        booking = Booking(
            host_id=kitchen.host_id,
            customer_id=user.id,
            kitchen_id=kitchen.id,
            status=BookingStatus.CONFIRMED,
            start_time=payload.start_time,
            end_time=payload.end_time,
            total_amount=total_amount,
            platform_fee=platform_fee,
            host_payout_amount=max(total_amount - platform_fee, 0),
            source="mobile-quick",
        )
        self.session.add(booking)
        await self.session.commit()
        await self.session.refresh(booking)

        summary = MobileBookingSummary(
            booking_id=booking.id,
            kitchen_id=kitchen.id,
            kitchen_name=kitchen.name,
            status=booking.status.value,
            start_time=booking.start_time,
            end_time=booking.end_time,
            role="customer",
        )
        return QuickBookingResponse(booking=summary, created=True)

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    async def register_push_token(
        self,
        user: User,
        payload: NotificationRegistrationRequest,
    ) -> NotificationRegistrationResponse:
        key = f"mobile:push:{payload.device.device_id}"
        expires_at = datetime.now(UTC) + timedelta(seconds=self.PUSH_REGISTRATION_TTL)
        record = {
            "user_id": str(user.id),
            "push_token": payload.push_token,
            "platform": payload.device.platform,
            "locale": payload.locale,
            "registered_at": datetime.now(UTC).isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        await self.redis.setex(key, self.PUSH_REGISTRATION_TTL, json.dumps(record))
        return NotificationRegistrationResponse(registered=True, expires_at=expires_at)

    # ------------------------------------------------------------------
    # Offline sync
    # ------------------------------------------------------------------
    async def sync_offline_data(
        self,
        user: User,
        *,
        background_interval_minutes: int | None,
    ) -> OfflineSyncResponse:
        stmt = (
            select(Kitchen, KitchenMatchingProfile)
            .join(
                KitchenMatchingProfile,
                KitchenMatchingProfile.kitchen_id == Kitchen.id,
                isouter=True,
            )
            .where(Kitchen.published.is_(True))
            .where(Kitchen.moderation_status == "approved")
            .order_by(Kitchen.trust_score.desc().nullslast())
            .limit(25)
        )
        kitchens_result = await self.session.execute(stmt)
        kitchen_map: dict[UUID, MobileKitchenSummary] = {}
        for kitchen, _ in kitchens_result.all():
            kitchen_map[kitchen.id] = MobileKitchenSummary(
                kitchen_id=kitchen.id,
                name=kitchen.name,
                distance_km=None,
                city=kitchen.city,
                state=kitchen.state,
                hourly_rate=float(kitchen.hourly_rate) if kitchen.hourly_rate is not None else None,
                trust_score=float(kitchen.trust_score) if kitchen.trust_score is not None else None,
                normalized_rating=None,
                rating_count=0,
            )

        preference = await self.session.get(UserMatchingPreference, user.id)
        if preference and preference.preferred_cities:
            city = preference.preferred_cities[0]
            matches = await self.matching_service.recommend_top_kitchens_for_city(city, limit=5)
            for match in matches:
                summary = self._summary_from_match(match)
                existing = kitchen_map.get(summary.kitchen_id)
                if existing is None:
                    kitchen_map[summary.kitchen_id] = summary
                else:
                    if existing.trust_score is None:
                        existing.trust_score = summary.trust_score
                    if existing.normalized_rating is None:
                        existing.normalized_rating = summary.normalized_rating

        all_ids = list(kitchen_map.keys())
        rating_map = await self.rating_service.get_rating_map(all_ids)
        for summary in kitchen_map.values():
            rating = rating_map.get(summary.kitchen_id)
            if rating:
                summary.normalized_rating = rating.normalized_score
                summary.rating_count = rating.external_count + rating.internal_count

        kitchens = list(kitchen_map.values())[:30]

        bookings_response = await self.upcoming_bookings(user)

        preferences_payload: dict[str, Any]
        if preference:
            preferences_payload = {
                "equipment": preference.equipment,
                "certifications": preference.certifications,
                "cuisines": preference.cuisines,
                "preferred_cities": preference.preferred_cities,
                "preferred_states": preference.preferred_states,
                "availability": preference.availability,
                "min_price": preference.min_price,
                "max_price": preference.max_price,
                "max_distance_km": preference.max_distance_km,
            }
        else:
            preferences_payload = {}

        generated_at = datetime.now(UTC)
        next_sync = (
            generated_at + timedelta(minutes=background_interval_minutes)
            if background_interval_minutes
            else None
        )

        snapshot = OfflineSyncResponse(
            user_id=user.id,
            kitchens=kitchens,
            bookings=bookings_response.items,
            preferences=preferences_payload,
            generated_at=generated_at,
            next_background_sync=next_sync,
        )

        cache_key = self._offline_cache_key(user.id)
        await self.redis.setex(cache_key, self.OFFLINE_CACHE_TTL, snapshot.model_dump_json())
        if background_interval_minutes:
            await self.redis.setex(
                self._background_key(user.id),
                self.OFFLINE_CACHE_TTL,
                str(background_interval_minutes),
            )

        perf_key = self._performance_key(user.id)
        perf_raw = await self.redis.get(perf_key)
        perf_record: dict[str, Any]
        if isinstance(perf_raw, str):
            try:
                perf_record = json.loads(perf_raw)
            except ValueError:
                perf_record = {}
        else:
            perf_record = {}
        perf_record["last_sync_at"] = generated_at.isoformat()
        perf_record.setdefault("latency_avg_ms", 120.0)
        perf_record.setdefault("latency_p95_ms", 220.0)
        perf_record.setdefault("offline_sync_success_rate", 0.97)
        perf_record.setdefault("issue_count", 0)
        await self.redis.setex(perf_key, self.PERFORMANCE_TTL, json.dumps(perf_record))

        return snapshot

    async def upload_offline_actions(
        self,
        user: User,
        payload: OfflineUploadRequest,
    ) -> OfflineUploadResponse:
        key = self._offline_queue_key(user.id)
        existing_raw = await self.redis.get(key)
        existing: list[dict[str, Any]] = []
        if isinstance(existing_raw, str):
            try:
                existing = json.loads(existing_raw)
            except ValueError:
                existing = []

        for action in payload.actions:
            existing.append(action.model_dump())

        await self.redis.setex(
            key, self.OFFLINE_CACHE_TTL, json.dumps(existing, default=self._json_default)
        )
        return OfflineUploadResponse(
            processed=len(payload.actions), queued=len(existing), next_sync_hint_minutes=30
        )

    async def cache_status(self, user: User) -> CacheStatusResponse:
        snapshot_raw = await self.redis.get(self._offline_cache_key(user.id))
        queue_raw = await self.redis.get(self._offline_queue_key(user.id))
        interval_raw = await self.redis.get(self._background_key(user.id))

        last_synced_at: datetime | None = None
        if isinstance(snapshot_raw, str):
            try:
                snapshot = json.loads(snapshot_raw)
                last_synced_at = datetime.fromisoformat(snapshot.get("generated_at"))
            except (ValueError, TypeError):
                last_synced_at = None

        pending_actions = 0
        if isinstance(queue_raw, str):
            try:
                pending_actions = len(json.loads(queue_raw))
            except ValueError:
                pending_actions = 0

        interval = int(interval_raw) if interval_raw else None

        return CacheStatusResponse(
            has_sync_snapshot=snapshot_raw is not None,
            last_synced_at=last_synced_at,
            pending_actions=pending_actions,
            background_interval_minutes=interval,
        )

    def _offline_cache_key(self, user_id: UUID) -> str:
        return f"mobile:offline:{user_id}"

    def _offline_queue_key(self, user_id: UUID) -> str:
        return f"mobile:offline-queue:{user_id}"

    def _background_key(self, user_id: UUID) -> str:
        return f"mobile:background:{user_id}"

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    async def quick_search(
        self,
        filters: QuickSearchFilters,
    ) -> QuickSearchResponse:
        if not filters.query and filters.city:
            matches = await self.matching_service.recommend_top_kitchens_for_city(
                filters.city, limit=filters.limit
            )
            items = [self._summary_from_match(match) for match in matches]
            return QuickSearchResponse(items=items, generated_at=datetime.now(UTC))

        stmt = (
            select(Kitchen)
            .where(Kitchen.published.is_(True))
            .where(Kitchen.moderation_status == "approved")
        )

        if filters.query:
            pattern = f"%{filters.query.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Kitchen.name).like(pattern),
                    func.lower(Kitchen.description).like(pattern),
                    func.lower(Kitchen.city).like(pattern),
                )
            )

        if filters.city:
            stmt = stmt.where(func.lower(Kitchen.city) == filters.city.lower())
        if filters.max_price is not None:
            stmt = stmt.where(Kitchen.hourly_rate <= filters.max_price)
        if filters.min_trust_score is not None:
            stmt = stmt.where(Kitchen.trust_score >= filters.min_trust_score)

        stmt = stmt.order_by(Kitchen.trust_score.desc().nullslast()).limit(filters.limit)

        result = await self.session.execute(stmt)
        kitchens = result.scalars().all()
        kitchen_ids = [kitchen.id for kitchen in kitchens]
        rating_map = await self.rating_service.get_rating_map(kitchen_ids)

        items: list[MobileKitchenSummary] = []
        for kitchen in kitchens:
            rating = rating_map.get(kitchen.id)
            normalized = rating.normalized_score if rating else None
            rating_count = 0
            if rating:
                rating_count = rating.external_count + rating.internal_count
            items.append(
                MobileKitchenSummary(
                    kitchen_id=kitchen.id,
                    name=kitchen.name,
                    distance_km=None,
                    city=kitchen.city,
                    state=kitchen.state,
                    hourly_rate=float(kitchen.hourly_rate)
                    if kitchen.hourly_rate is not None
                    else None,
                    trust_score=float(kitchen.trust_score)
                    if kitchen.trust_score is not None
                    else None,
                    normalized_rating=normalized,
                    rating_count=rating_count,
                )
            )

        return QuickSearchResponse(items=items, generated_at=datetime.now(UTC))

    # ------------------------------------------------------------------
    # Kitchen detail
    # ------------------------------------------------------------------
    async def kitchen_detail(self, kitchen_id: UUID) -> MobileKitchenDetailResponse:
        stmt = (
            select(Kitchen, KitchenMatchingProfile)
            .join(
                KitchenMatchingProfile,
                KitchenMatchingProfile.kitchen_id == Kitchen.id,
                isouter=True,
            )
            .where(Kitchen.id == kitchen_id)
        )
        result = await self.session.execute(stmt)
        data = result.one_or_none()
        if data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")

        kitchen, profile = data
        if not kitchen.published or kitchen.moderation_status != "approved":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not available"
            )

        rating_map = await self.rating_service.get_rating_map([kitchen.id])
        rating = rating_map.get(kitchen.id)
        summary = MobileKitchenSummary(
            kitchen_id=kitchen.id,
            name=kitchen.name,
            distance_km=None,
            city=kitchen.city,
            state=kitchen.state,
            hourly_rate=float(kitchen.hourly_rate) if kitchen.hourly_rate is not None else None,
            trust_score=float(kitchen.trust_score) if kitchen.trust_score is not None else None,
            normalized_rating=rating.normalized_score if rating else None,
            rating_count=(rating.external_count + rating.internal_count) if rating else 0,
        )

        external_sources: list[dict[str, Any]] = []
        if rating:
            for source in rating.external_sources:
                external_sources.append(source.model_dump())

        return MobileKitchenDetailResponse(
            kitchen=summary,
            description=kitchen.description,
            equipment=profile.equipment if profile else [],
            cuisines=profile.cuisines if profile else [],
            certifications=profile.certifications if profile else [],
            availability=profile.availability if profile else [],
            external_sources=external_sources,
        )

    # ------------------------------------------------------------------
    # Camera uploads
    # ------------------------------------------------------------------
    async def upload_camera_media(
        self,
        user: User,
        payload: CameraUploadRequest,
    ) -> CameraUploadResponse:
        _ = user  # currently unused, reserved for future access controls
        compression_ratio = 0.58
        compressed = max(1, int(payload.file_size_bytes * compression_ratio))
        latency = max(40, int(payload.file_size_bytes / 1024))
        cache_key = f"mobile:camera:{payload.kitchen_id}:{uuid4()}"
        record = {
            "kitchen_id": str(payload.kitchen_id),
            "file_name": payload.file_name,
            "content_type": payload.content_type,
            "original_size": payload.file_size_bytes,
            "compressed_size": compressed,
            "uploaded_at": datetime.now(UTC).isoformat(),
        }
        await self.redis.setex(cache_key, self.SESSION_CACHE_TTL, json.dumps(record))
        return CameraUploadResponse(
            uploaded=True,
            compressed_size_bytes=compressed,
            processing_latency_ms=latency,
            cache_key=cache_key,
        )

    # ------------------------------------------------------------------
    # Biometric authentication
    # ------------------------------------------------------------------
    async def register_biometric(
        self,
        user: User,
        payload: BiometricRegistrationRequest,
    ) -> BiometricRegistrationResponse:
        key = self._biometric_key(user.id, payload.device.device_id)
        secret_hash = sha256(payload.biometric_key.encode()).hexdigest()
        record = {
            "user_id": str(user.id),
            "device_id": payload.device.device_id,
            "secret_hash": secret_hash,
            "registered_at": datetime.now(UTC).isoformat(),
        }
        await self.redis.setex(key, self.PUSH_REGISTRATION_TTL, json.dumps(record))
        await self._update_biometric_index(key)
        return BiometricRegistrationResponse(registered=True, registered_at=datetime.now(UTC))

    async def verify_biometric(
        self,
        payload: BiometricVerificationRequest,
    ) -> BiometricVerificationResponse:
        candidates = await self._load_biometric_index()
        signature_hash = sha256(payload.signature.encode()).hexdigest()
        for key in candidates:
            if not key.endswith(f":{payload.device_id}"):
                continue
            record_raw = await self.redis.get(key)
            if not isinstance(record_raw, str):
                continue
            try:
                record = json.loads(record_raw)
            except ValueError:
                continue
            if record.get("secret_hash") != signature_hash:
                continue
            try:
                user_id = UUID(record["user_id"])
            except (KeyError, ValueError):
                continue
            stmt = select(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            if user is None or not user.is_active or user.is_suspended:
                continue
            tokens = self._issue_tokens(user)
            await self._cache_session(user.id, payload.device_id, tokens, None)
            return BiometricVerificationResponse(verified=True, tokens=tokens)
        return BiometricVerificationResponse(verified=False, tokens=None)

    async def biometric_status(
        self,
        user: User,
        device_id: str,
    ) -> BiometricStatusResponse:
        key = self._biometric_key(user.id, device_id)
        record_raw = await self.redis.get(key)
        registered = False
        registered_at: datetime | None = None
        if isinstance(record_raw, str):
            try:
                record = json.loads(record_raw)
            except ValueError:
                record = None
            if record:
                registered = True
                registered_at = datetime.fromisoformat(record.get("registered_at"))
        return BiometricStatusResponse(
            device_id=device_id, registered=registered, registered_at=registered_at
        )

    def _biometric_key(self, user_id: UUID, device_id: str) -> str:
        return f"mobile:biometric:{user_id}:{device_id}"

    async def _update_biometric_index(self, key: str) -> None:
        index_key = "mobile:biometric:index"
        index_raw = await self.redis.get(index_key)
        entries: list[str] = []
        if isinstance(index_raw, str):
            try:
                entries = json.loads(index_raw)
            except ValueError:
                entries = []
        if key not in entries:
            entries.append(key)
        await self.redis.setex(index_key, self.PUSH_REGISTRATION_TTL, json.dumps(entries))

    async def _load_biometric_index(self) -> list[str]:
        index_key = "mobile:biometric:index"
        index_raw = await self.redis.get(index_key)
        if isinstance(index_raw, str):
            try:
                return list(json.loads(index_raw))
            except ValueError:
                return []
        return []

    # ------------------------------------------------------------------
    # Performance metrics
    # ------------------------------------------------------------------
    async def performance_metrics(self, user: User) -> PerformanceMetricsResponse:
        key = self._performance_key(user.id)
        record_raw = await self.redis.get(key)
        if isinstance(record_raw, str):
            try:
                record = json.loads(record_raw)
            except ValueError:
                record = {}
        else:
            record = {}

        latency_avg = float(record.get("latency_avg_ms", 120.0))
        latency_p95 = float(record.get("latency_p95_ms", 220.0))
        offline_rate = float(record.get("offline_sync_success_rate", 0.97))
        last_sync = record.get("last_sync_at")
        last_sync_at = datetime.fromisoformat(last_sync) if last_sync else None
        issue_count = int(record.get("issue_count", 0))

        return PerformanceMetricsResponse(
            latency_avg_ms=latency_avg,
            latency_p95_ms=latency_p95,
            offline_sync_success_rate=offline_rate,
            last_sync_at=last_sync_at,
            issue_count=issue_count,
        )

    async def report_performance_issue(
        self,
        user: User,
        payload: PerformanceReportRequest,
    ) -> PerformanceReportResponse:
        key = self._performance_key(user.id)
        record_raw = await self.redis.get(key)
        if isinstance(record_raw, str):
            try:
                record = json.loads(record_raw)
            except ValueError:
                record = {}
        else:
            record = {}

        record.setdefault("issues", []).append(payload.model_dump())
        record["issue_count"] = len(record["issues"])
        record.setdefault("last_sync_at", datetime.now(UTC).isoformat())

        await self.redis.setex(
            key, self.PERFORMANCE_TTL, json.dumps(record, default=self._json_default)
        )
        reference = f"PERF-{uuid4()}"
        return PerformanceReportResponse(accepted=True, reference_id=reference)

    def _performance_key(self, user_id: UUID) -> str:
        return f"mobile:performance:{user_id}"

    # ------------------------------------------------------------------
    # Bandwidth estimation
    # ------------------------------------------------------------------
    async def bandwidth_estimate(self, user: User) -> BandwidthEstimateResponse:
        cache_key = self._offline_cache_key(user.id)
        snapshot_raw = await self.redis.get(cache_key)
        basis = "historical-average"
        if isinstance(snapshot_raw, str):
            try:
                snapshot = json.loads(snapshot_raw)
            except ValueError:
                snapshot = {}
            size = len(snapshot_raw.encode())
            estimated_kbps = round((size * 8) / 1024, 2)
            basis = "offline-cache"
        else:
            estimated_kbps = 256.0
        return BandwidthEstimateResponse(
            estimated_kbps=estimated_kbps,
            basis=basis,
            last_measurement_at=datetime.now(UTC),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _summary_from_match(self, match: KitchenMatchModel) -> MobileKitchenSummary:
        return MobileKitchenSummary(
            kitchen_id=match.kitchen_id,
            name=match.kitchen_name,
            distance_km=None,
            city=match.city,
            state=match.state,
            hourly_rate=match.hourly_rate,
            trust_score=match.trust_score,
            normalized_rating=match.external_rating,
            rating_count=0,
        )

    def _json_default(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, Decimal):
            return float(value)
        return value

    async def _get_background_interval(self, user_id: UUID) -> int | None:
        raw = await self.redis.get(self._background_key(user_id))
        if isinstance(raw, str):
            try:
                return int(raw)
            except ValueError:
                return None
        return None
