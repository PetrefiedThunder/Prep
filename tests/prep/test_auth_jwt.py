"""Tests for JWT verification in :mod:`prep.auth`."""

from __future__ import annotations

import base64
import json

import jwt
import pytest
from fastapi import HTTPException, status

from prep.auth import _decode_jwt
from prep.settings import Settings


def _make_settings(secret: str = "super-secret") -> Settings:
    return Settings(secret_key=secret)


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def test_decode_jwt_valid_token() -> None:
    settings = _make_settings()
    payload = {"sub": "123", "roles": ["admin"]}
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")

    decoded = _decode_jwt(token, settings)

    assert decoded["sub"] == "123"
    assert decoded["roles"] == ["admin"]


def test_decode_jwt_invalid_signature() -> None:
    settings = _make_settings()
    payload = {"sub": "123"}
    forged = jwt.encode(payload, "wrong-key", algorithm="HS256")

    with pytest.raises(HTTPException) as exc:
        _decode_jwt(forged, settings)

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_decode_jwt_tampered_payload() -> None:
    settings = _make_settings()
    payload = {"sub": "123", "roles": ["customer"]}
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    header, _, signature = token.split(".")
    tampered_payload = _b64_encode(json.dumps({"sub": "456"}).encode("utf-8"))
    tampered = "".join([header, ".", tampered_payload, ".", signature])

    with pytest.raises(HTTPException) as exc:
        _decode_jwt(tampered, settings)

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_decode_jwt_rejects_unsupported_algorithm() -> None:
    settings = _make_settings()
    header = _b64_encode(json.dumps({"alg": "none", "typ": "JWT"}).encode("utf-8"))
    payload = _b64_encode(json.dumps({"sub": "123"}).encode("utf-8"))
    token = f"{header}.{payload}."

    with pytest.raises(HTTPException) as exc:
        _decode_jwt(token, settings)

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
