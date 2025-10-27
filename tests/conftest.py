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
        "DateTime",
        "Enum",
        "Float",
        "ForeignKey",
        "Integer",
        "JSON",
        "Numeric",
        "String",
        "Text",
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
