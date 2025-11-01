from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types
from typing import Generator, Iterator

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SKIP_PREP_DB_INIT", "1")

# Optional dependencies -----------------------------------------------------

def _ensure_sqlalchemy_stub() -> None:
    if importlib.util.find_spec("sqlalchemy") is not None:
        return

    sqlalchemy_stub = types.ModuleType("sqlalchemy")
    sqlalchemy_stub.__prep_stub__ = True

    class _Placeholder:
        def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: D401
            """Placeholder SQLAlchemy construct used in tests."""

    names = [
        "Column",
        "Integer",
        "String",
        "Boolean",
        "Date",
        "DateTime",
        "Float",
        "Numeric",
        "Enum",
        "JSON",
        "ForeignKey",
        "UniqueConstraint",
        "Index",
    ]
    for name in names:
        setattr(sqlalchemy_stub, name, _Placeholder)

    sqlalchemy_stub.exc = types.SimpleNamespace(OperationalError=Exception)
    sys.modules["sqlalchemy"] = sqlalchemy_stub


def _ensure_aiohttp_stub() -> None:
    if "aiohttp" in sys.modules:
        return

    sys.modules["sqlalchemy"] = sqlalchemy_stub
    sys.modules["sqlalchemy.orm"] = orm_module
    sys.modules["sqlalchemy.pool"] = pool_module
    sys.modules["sqlalchemy.dialects"] = dialects_module
    sys.modules["sqlalchemy.dialects.postgresql"] = postgresql_module
    sys.modules["sqlalchemy.types"] = types_module
    sys.modules["sqlalchemy.ext"] = ext_module


_sqlalchemy_spec = importlib.util.find_spec("sqlalchemy")
if _sqlalchemy_spec is None:
    _ensure_sqlalchemy_stub()
    sys.modules["sqlalchemy.ext.mutable"] = mutable_module

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

SessionLocal = None  # type: ignore[assignment]
init_db = None  # type: ignore[assignment]

if _sqlalchemy_spec is not None:  # pragma: no branch - skip when SQLAlchemy is stubbed
    try:  # pragma: no cover - dependency availability varies per environment
        from prep.models.db import SessionLocal as _SessionLocal, init_db as _init_db  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - allow tests without SQLAlchemy
        if exc.name != "sqlalchemy":
            raise
    except SyntaxError:  # pragma: no cover - legacy ORM definitions may not parse
        pass
    except Exception:  # pragma: no cover - defensive fallback for optional dependency
        pass
    else:
        SessionLocal = _SessionLocal  # type: ignore[assignment]
        init_db = _init_db  # type: ignore[assignment]

if getattr(sys.modules.get("sqlalchemy"), "__prep_stub__", False):
    SessionLocal = None  # type: ignore[assignment]
    init_db = None  # type: ignore[assignment]

if os.getenv("SKIP_DB_SETUP") == "1":
    SessionLocal = None  # type: ignore[assignment]
    init_db = None  # type: ignore[assignment]
    db_module = sys.modules.get("prep.models.db")
    if db_module is not None:
        setattr(db_module, "init_db", lambda: None)
        setattr(db_module, "SessionLocal", None)
if "aiohttp" not in sys.modules:
    try:
        import aiohttp as _aiohttp  # noqa: F401  # pragma: no cover - prefer real module
    except ModuleNotFoundError:  # pragma: no cover - lightweight environments
        aiohttp_stub = types.ModuleType("aiohttp")

        class ClientError(Exception):
            pass

        class ClientSession:  # noqa: D401 - simple stub
            """Placeholder aiohttp.ClientSession."""

            async def __aenter__(self) -> "ClientSession":
                return self

            async def __aexit__(self, *exc_info: object) -> None:
                return None

        class ClientTimeout:  # noqa: D401 - simple stub
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

        class TCPConnector:  # noqa: D401 - simple stub
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

        aiohttp_stub.ClientError = ClientError
        aiohttp_stub.ClientSession = ClientSession
        aiohttp_stub.ClientTimeout = ClientTimeout
        aiohttp_stub.TCPConnector = TCPConnector
        sys.modules["aiohttp"] = aiohttp_stub


def _ensure_boto3_stub() -> None:
    if "boto3" in sys.modules:
        return

    try:
        import boto3 as _boto3  # noqa: F401  # pragma: no cover - prefer real module
    except ModuleNotFoundError:  # pragma: no cover - fallback stub
        boto3_stub = types.ModuleType("boto3")

        class _Client:
            def __init__(self, service_name: str) -> None:
                self.service_name = service_name

            def close(self) -> None:  # noqa: D401 - simple stub
                """No-op close method for the boto3 stub."""

            def __getattr__(self, name: str) -> types.FunctionType:
                def _missing(*args: object, **kwargs: object) -> None:
                    raise NotImplementedError(
                        "boto3 is unavailable in this lightweight test environment"
                    )

                return _missing

        def client(service_name: str, *args: object, **kwargs: object) -> _Client:
            return _Client(service_name)

        boto3_stub.client = client
        sys.modules["boto3"] = boto3_stub


_ensure_sqlalchemy_stub()
_ensure_aiohttp_stub()
_ensure_boto3_stub()

SessionLocal = None
init_db = None

try:
    from prep.models.db import SessionLocal as _SessionLocal, init_db as _init_db
except (ModuleNotFoundError, SyntaxError):  # pragma: no cover - optional dependency
    pass
except Exception:  # pragma: no cover - defensive fallback when ORM cannot be imported
    SessionLocal = None
    init_db = None
else:
    if getattr(sys.modules.get("sqlalchemy"), "__prep_stub__", False):
        SessionLocal = None
        init_db = None
    else:
        SessionLocal = _SessionLocal
        init_db = _init_db


# Fixtures ------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> Generator[None, None, None]:
    global init_db  # noqa: PLW0603 - test environment setup

    if init_db is None or os.environ.get("SKIP_PREP_DB_INIT") == "1":
        yield
        return

    try:
        init_db()
    except Exception:  # pragma: no cover - database optional in lightweight envs
        init_db = None
        yield
        return

    yield


@pytest.fixture
def db_session() -> Iterator[object]:
    if SessionLocal is None:
        pytest.skip("Database layer is not available in this environment")

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
