import asyncio
import importlib.util
import os
import sys
import types
from typing import Any, Callable

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

if importlib.util.find_spec("sqlalchemy") is None:
    sqlalchemy_stub = types.ModuleType("sqlalchemy")

    class _SQLType:
        def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: D401
            """Placeholder SQLAlchemy column type."""

    def _unavailable(*args: object, **kwargs: object) -> None:  # noqa: D401
        """Placeholder factory used in tests without SQLAlchemy."""

    for name in [
        "Boolean",
        "Date",
        "DateTime",
        "Enum",
        "Float",
        "ForeignKey",
        "Integer",
        "JSON",
        "Numeric",
        "String",
        "Text",
        "UniqueConstraint",
        "select",
    ]:
        setattr(sqlalchemy_stub, name, _SQLType)

    def create_engine(*args: object, **kwargs: object) -> types.SimpleNamespace:
        return types.SimpleNamespace()

    sqlalchemy_stub.create_engine = create_engine

    orm_module = types.ModuleType("sqlalchemy.orm")

    class DeclarativeBase:
        metadata = types.SimpleNamespace(create_all=lambda bind: None)

    def declared_attr(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    def mapped_column(*args: object, **kwargs: object) -> None:
        return None

    def relationship(*args: object, **kwargs: object) -> None:
        return None

    class sessionmaker:
        def __init__(self, **_: object) -> None:
            pass

        def __call__(self) -> types.SimpleNamespace:
            return types.SimpleNamespace(commit=lambda: None, rollback=lambda: None, close=lambda: None)

    orm_module.DeclarativeBase = DeclarativeBase
    orm_module.Mapped = Any
    orm_module.declared_attr = types.SimpleNamespace(directive=staticmethod(lambda func: func))
    orm_module.mapped_column = mapped_column
    orm_module.relationship = relationship
    orm_module.sessionmaker = sessionmaker
    orm_module.Session = Any

    pool_module = types.ModuleType("sqlalchemy.pool")

    class StaticPool:  # noqa: D401
        """Placeholder static pool implementation."""

    pool_module.StaticPool = StaticPool

    dialects_module = types.ModuleType("sqlalchemy.dialects")
    postgresql_module = types.ModuleType("sqlalchemy.dialects.postgresql")

    class UUID:  # noqa: D401
        """Placeholder UUID column type."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

    postgresql_module.UUID = UUID
    dialects_module.postgresql = postgresql_module

    types_module = types.ModuleType("sqlalchemy.types")

    class TypeDecorator:  # noqa: D401
        """Placeholder type decorator."""

        impl = None

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __class_getitem__(cls, _: object) -> "TypeDecorator":
            return cls

    class CHAR(_SQLType):
        pass

    types_module.TypeDecorator = TypeDecorator
    types_module.CHAR = CHAR

    sys.modules["sqlalchemy"] = sqlalchemy_stub
    sys.modules["sqlalchemy.orm"] = orm_module
    sys.modules["sqlalchemy.pool"] = pool_module
    sys.modules["sqlalchemy.dialects"] = dialects_module
    sys.modules["sqlalchemy.dialects.postgresql"] = postgresql_module
    sys.modules["sqlalchemy.types"] = types_module

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

try:  # pragma: no cover - dependency availability varies per environment
    from prep.models.db import SessionLocal, init_db  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - allow tests without SQLAlchemy
    if exc.name != "sqlalchemy":
        raise
    SessionLocal = None  # type: ignore
    init_db = None  # type: ignore
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
    global init_db  # noqa: PLW0603 - test environment setup
    if init_db is None:
        yield
        return

    try:
        init_db()
    except Exception:  # pragma: no cover - defensive fallback for missing deps
        init_db = None
        yield
        return
    yield


@pytest.fixture
def db_session():
    if SessionLocal is None:
        pytest.skip("SQLAlchemy is not available in the test environment")
        pytest.skip("Database layer is not available in this environment")

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
