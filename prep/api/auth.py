"""Authentication API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

try:  # pragma: no cover - exercised indirectly via tests
    import email_validator  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover - environment without optional dependency
    class EmailStr(str):
        """Fallback EmailStr implementation when ``email_validator`` is absent."""

        @classmethod
        def __get_pydantic_core_schema__(
            cls, source_type: type[Any], handler: GetCoreSchemaHandler
        ) -> CoreSchema:
            return handler(str)

        @classmethod
        def __get_pydantic_json_schema__(
            cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
        ) -> JsonSchemaValue:
            return handler(core_schema)

else:  # pragma: no cover - exercised when optional dependency installed
    from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database.connection import get_db
from prep.models import SubscriptionStatus, User, UserRole
from prep.pilot import resolve_pilot_membership
from prep.settings import Settings, get_settings
from prep.utils.jwt import create_access_token
from prep.utils.password import get_password_hash, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class UserCreate(BaseModel):
    """Payload for user registration."""

    name: str
    email: EmailStr
    password: str
    role: str
    zip_code: str | None = None
    county: str | None = None


class UserLogin(BaseModel):
    """Payload for user login."""

    email: EmailStr
    password: str


class AuthenticatedUser(BaseModel):
    """Serialized representation of the authenticated user."""

    id: str
    email: EmailStr
    name: str
    role: str
    is_pilot_user: bool
    subscription_status: str
    trial_ends_at: datetime | None = None
    pilot_county: str | None = None
    pilot_zip_code: str | None = None


class AuthResponse(BaseModel):
    """JWT bearer token response with user metadata."""

    access_token: str
    token_type: str
    user: AuthenticatedUser


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    """Register a new user and return an access token."""

    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    try:
        role = UserRole(user_data.role.lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported role"
        ) from exc

    pilot_resolution = resolve_pilot_membership(user_data.zip_code, user_data.county, settings)
    hashed_password = get_password_hash(user_data.password)

    now = datetime.now(UTC)
    trial_started_at = now if pilot_resolution.is_pilot else None
    trial_ends_at = now + timedelta(days=60) if pilot_resolution.is_pilot else None
    subscription_status = (
        SubscriptionStatus.TRIAL if pilot_resolution.is_pilot else SubscriptionStatus.INACTIVE
    )

    new_user = User(
        full_name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_password,
        role=role,
        is_pilot_user=pilot_resolution.is_pilot,
        pilot_zip_code=pilot_resolution.matched_zip,
        pilot_county=pilot_resolution.matched_county,
        subscription_status=subscription_status,
        trial_started_at=trial_started_at,
        trial_ends_at=trial_ends_at,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token({"sub": str(new_user.id), "role": new_user.role.value})
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=_serialize_user(new_user),
    )


@router.post("/login", response_model=AuthResponse)
async def login_user(user_data: UserLogin, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Authenticate a user and return a bearer token."""

    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user.last_login_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return AuthResponse(access_token=access_token, token_type="bearer", user=_serialize_user(user))


def _serialize_user(user: User) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=str(user.id),
        email=user.email,
        name=user.full_name,
        role=user.role.value,
        is_pilot_user=bool(user.is_pilot_user),
        subscription_status=user.subscription_status.value,
        trial_ends_at=user.trial_ends_at,
        pilot_county=user.pilot_county,
        pilot_zip_code=user.pilot_zip_code,
    )
