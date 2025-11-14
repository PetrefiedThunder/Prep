from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.database import get_db
from prep.models.orm import Base, Booking, BookingStatus, Kitchen, SubleaseContract, User
from prep.platform.api import (
    get_docusign_client,
    get_s3_client,
    get_settings,
    router,
)
from prep.settings import Settings

pytestmark = pytest.mark.anyio("asyncio")


class StubDocuSignClient:
    def __init__(self) -> None:
        self.last_envelope_id = "env-123"
        self.signing_url = "https://sign.example.com/abc"
        self.status: str = "sent"
        self.document_bytes = b"%PDF-1.4"
        self.last_send_kwargs: dict[str, Any] | None = None
        self.requested_status_envelope: str | None = None
        self.downloaded_envelope: str | None = None

    def send_template(self, **kwargs: Any) -> tuple[str, str]:
        self.last_send_kwargs = kwargs
        return self.last_envelope_id, self.signing_url

    def get_envelope_status(self, envelope_id: str) -> str:
        self.requested_status_envelope = envelope_id
        return self.status

    def download_document(self, envelope_id: str, document_id: str = "combined") -> bytes:
        self.downloaded_envelope = envelope_id
        return self.document_bytes


class StubS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:  # noqa: N803 (AWS naming)
        self.objects[(Bucket, Key)] = Body


@pytest.fixture()
async def app() -> AsyncGenerator[FastAPI, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    application = FastAPI()
    application.include_router(router)
    application.state.session_factory = session_factory

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    settings = Settings(
        environment="development",
        docusign_account_id="acct-123",
        docusign_access_token="token-abc",
        docusign_sublease_template_id="tmpl-456",
        docusign_return_url="https://app.example.com/docusign/return",
        contracts_s3_bucket="test-contracts",
    )

    docusign_stub = StubDocuSignClient()
    s3_stub = StubS3Client()
    application.state.docusign_stub = docusign_stub
    application.state.s3_stub = s3_stub

    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[get_docusign_client] = lambda: docusign_stub
    application.dependency_overrides[get_s3_client] = lambda: s3_stub

    try:
        yield application
    finally:
        application.dependency_overrides.clear()
        await engine.dispose()


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


async def _seed_booking(app: FastAPI) -> UUID:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        host = User(
            email="host@example.com",
            full_name="Host User",
            hashed_password="hashed",
        )
        customer = User(
            email="customer@example.com",
            full_name="Customer",
            hashed_password="hashed",
        )
        session.add_all([host, customer])
        await session.flush()

        kitchen = Kitchen(
            name="Downtown Kitchen",
            description="A commercial kitchen",
            host_id=host.id,
            city="Seattle",
            state="WA",
            hourly_rate=85,
            trust_score=4.3,
            moderation_status="approved",
            certification_status="approved",
            published=True,
        )
        session.add(kitchen)
        await session.flush()

        now = datetime.now(UTC)
        booking = Booking(
            host_id=host.id,
            customer_id=customer.id,
            kitchen_id=kitchen.id,
            status=BookingStatus.CONFIRMED,
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=4),
            total_amount=320,
            platform_fee=32,
            host_payout_amount=288,
            payment_method="card",
        )
        session.add(booking)
        await session.commit()
        return booking.id


async def test_send_sublease_contract_persists_envelope(app: FastAPI, client: AsyncClient) -> None:
    booking_id = await _seed_booking(app)
    docusign_stub: StubDocuSignClient = app.state.docusign_stub

    payload = {
        "booking_id": str(booking_id),
        "signer_email": "customer@example.com",
        "signer_name": "Customer Example",
    }

    response = await client.post("/api/v1/platform/contracts/sublease/send", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["envelope_id"] == docusign_stub.last_envelope_id
    assert data["sign_url"] == docusign_stub.signing_url
    assert docusign_stub.last_send_kwargs is not None
    assert docusign_stub.last_send_kwargs["template_id"] == "tmpl-456"
    assert docusign_stub.last_send_kwargs["signer_email"] == "customer@example.com"

    session_factory = app.state.session_factory
    async with session_factory() as session:
        stmt: Select[tuple[SubleaseContract]] = select(SubleaseContract).where(
            SubleaseContract.booking_id == booking_id
        )
        result = await session.execute(stmt)
        contract = result.scalar_one()
        assert contract.envelope_id == docusign_stub.last_envelope_id
        assert contract.sign_url == docusign_stub.signing_url


async def test_get_sublease_contract_status_uploads_pdf(app: FastAPI, client: AsyncClient) -> None:
    booking_id = await _seed_booking(app)
    docusign_stub: StubDocuSignClient = app.state.docusign_stub
    s3_stub: StubS3Client = app.state.s3_stub

    await client.post(
        "/api/v1/platform/contracts/sublease/send",
        json={
            "booking_id": str(booking_id),
            "signer_email": "customer@example.com",
        },
    )

    docusign_stub.status = "completed"

    response = await client.get(
        f"/api/v1/platform/contracts/sublease/status/{booking_id}",
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "completed"
    assert data["document_s3_bucket"] == "test-contracts"
    assert data["document_s3_key"].startswith("sublease-contracts/")
    assert docusign_stub.downloaded_envelope == docusign_stub.last_envelope_id
    assert ("test-contracts", data["document_s3_key"]) in s3_stub.objects

    session_factory = app.state.session_factory
    async with session_factory() as session:
        stmt: Select[tuple[SubleaseContract]] = select(SubleaseContract).where(
            SubleaseContract.booking_id == booking_id
        )
        result = await session.execute(stmt)
        contract = result.scalar_one()
        assert contract.status.value == "completed"
        assert contract.document_s3_bucket == "test-contracts"
        assert contract.document_s3_key == data["document_s3_key"]
        assert contract.completed_at is not None
