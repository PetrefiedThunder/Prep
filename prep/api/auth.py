"""Authentication API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database.connection import get_db
from prep.models import User
from prep.utils.jwt import create_access_token
from prep.utils.password import get_password_hash, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class UserCreate(BaseModel):
    """Payload for user registration."""

    name: str
    email: EmailStr
    password: str
    role: str


class UserLogin(BaseModel):
    """Payload for user login."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT bearer token response."""

    access_token: str
    token_type: str


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)) -> Token:
    """Register a new user and return an access token."""

    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,
        role=user_data.role,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token({"sub": str(new_user.id), "role": new_user.role})
    return Token(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=Token)
async def login_user(user_data: UserLogin, db: AsyncSession = Depends(get_db)) -> Token:
    """Authenticate a user and return a bearer token."""

    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return Token(access_token=access_token, token_type="bearer")
