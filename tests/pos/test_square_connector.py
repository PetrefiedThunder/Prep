from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

httpx = pytest.importorskip("httpx")
sqlalchemy_asyncio = pytest.importorskip("sqlalchemy.ext.asyncio")

from httpx import MockTransport, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.models.orm import Base, POSIntegration
from prep.pos.repository import POSIntegrationRepository
from prep.pos.square import SquarePOSConnector

pytestmark = pytest.mark.anyio


def _mock_square_handler(request: httpx.Request) -> Response:  # pragma: no cover - helper
    if request.url.path.endswith("/oauth2/token"):
        return Response(
            200,
            json={
                "access_token": "access-token",
                "refresh_token": "new-refresh",
                "expires_at": "2024-01-01T00:00:00Z",
            },
        )
    if request.url.path.endswith("/v2/locations"):
        return Response(200, json={"locations": [{"id": "LOC-1"}]})
    if request.url.path.endswith("/v2/locations/LOC-1/transactions"):
        return Response(
            200,
            json={
                "transactions": [
                    {
                        "id": "txn-1",
                        "created_at": "2024-01-01T00:00:00Z",
                        "location_id": "LOC-1",
                        "tenders": [
                            {
                                "amount_money": {"amount": "2500", "currency": "USD"},
                                "type": "CARD",
                            }
                        ],
                    }
                ]
            },
        )
    return Response(404, json={})


@pytest.fixture()
async def session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


async def test_sync_integration_persists_transactions(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        integration = POSIntegration(
            kitchen_id=uuid4(),
            provider="square",
            refresh_token="refresh-token",
        )
        session.add(integration)
        await session.commit()
        await session.refresh(integration)

        transport = MockTransport(_mock_square_handler)
        async with httpx.AsyncClient(transport=transport, base_url="https://square.test") as client:
            connector = SquarePOSConnector(
                client_id="client-id",
                client_secret="client-secret",
                http_client=client,
                base_url="https://square.test",
            )
            repository = POSIntegrationRepository(session)
            transactions = await connector.sync_integration(
                repository=repository,
                integration=integration,
            )
        await session.commit()

        assert len(transactions) == 1
        saved = transactions[0]
        assert saved.external_id == "txn-1"
        assert saved.amount == Decimal("25")
        assert saved.currency == "USD"
        assert saved.location_id == "LOC-1"
        assert saved.occurred_at == datetime(2024, 1, 1, tzinfo=UTC)
        assert integration.access_token == "access-token"
        assert integration.refresh_token == "new-refresh"
