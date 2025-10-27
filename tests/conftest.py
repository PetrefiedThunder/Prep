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

if "aiohttp" not in sys.modules:
    try:
        import aiohttp as _aiohttp  # type: ignore  # pragma: no cover - prefer real installation when available
    except ModuleNotFoundError:  # pragma: no cover - fallback for lightweight environments
        aiohttp_stub = types.ModuleType("aiohttp")

        class _ClientError(Exception):
            """Fallback aiohttp client error."""

            pass

        class _ClientSession:
            """Placeholder aiohttp session."""

            pass

        class _ClientTimeout:
            def __init__(self, *args, **kwargs) -> None:  # noqa: D401 - simple stub
                """Placeholder for aiohttp.ClientTimeout."""

        class _TCPConnector:
            def __init__(self, *args, **kwargs) -> None:  # noqa: D401 - simple stub
                """Placeholder for aiohttp.TCPConnector."""

        aiohttp_stub.ClientError = _ClientError
        aiohttp_stub.ClientSession = _ClientSession
        aiohttp_stub.ClientTimeout = _ClientTimeout
        aiohttp_stub.TCPConnector = _TCPConnector

        sys.modules["aiohttp"] = aiohttp_stub

if "boto3" not in sys.modules:
    try:
        import boto3 as _boto3  # type: ignore  # pragma: no cover - prefer real installation when available
    except ModuleNotFoundError:  # pragma: no cover - fallback for lightweight environments
        boto3_stub = types.ModuleType("boto3")

        class _Client:
            def __init__(self, service_name: str) -> None:
                self._service_name = service_name

            def put_object(self, **kwargs) -> None:  # noqa: D401 - simple stub
                """Placeholder for boto3 client put_object."""
                raise NotImplementedError("boto3 is not installed")

            def close(self) -> None:
                pass

        def _client(service_name: str, *args, **kwargs):
            return _Client(service_name)

        boto3_stub.client = _client
        sys.modules["boto3"] = boto3_stub

try:
    from prep.models.db import SessionLocal, init_db
except ModuleNotFoundError:  # pragma: no cover - optional dependency for lightweight tests
    SessionLocal = None  # type: ignore[assignment]
    init_db = None  # type: ignore[assignment]


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    if init_db is None:
        yield
        return

    init_db()
    yield


@pytest.fixture
def db_session():
    if SessionLocal is None:
        pytest.skip("Database layer is not available in this environment")

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
