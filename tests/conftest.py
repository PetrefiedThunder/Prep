import asyncio
import os
import sys
import types

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

# Provide a lightweight Stripe stub for test environments without the SDK installed.
if "stripe" not in sys.modules:
    stripe_stub = types.ModuleType("stripe")
    stripe_stub.api_key = ""

    class _StripeError(Exception):
        """Fallback Stripe error type used in tests."""

        pass

    class _AccountAPI:
        def create(self, **_: object) -> None:
            raise NotImplementedError("Stripe SDK is not installed in the test environment")

    class _AccountLinkAPI:
        def create(self, **_: object) -> None:
            raise NotImplementedError("Stripe SDK is not installed in the test environment")

    stripe_stub.Account = _AccountAPI()
    stripe_stub.AccountLink = _AccountLinkAPI()

    error_module = types.ModuleType("stripe.error")
    error_module.StripeError = _StripeError
    stripe_stub.error = error_module

    sys.modules["stripe"] = stripe_stub
    sys.modules["stripe.error"] = error_module

from prep.models.db import SessionLocal, init_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    init_db()
    yield


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
