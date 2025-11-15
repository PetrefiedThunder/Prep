import pytest

wiremock = pytest.importorskip("wiremock")

from wiremock.client import Mappings
from wiremock.constants import Config
from wiremock.resources.mappings import Mapping, MappingRequest, MappingResponse
from wiremock.server import WireMockServer

from prep.regulatory.apis.insurance import NextInsuranceAPI, ThimbleAPI


@pytest.fixture(scope="module")
def wiremock_server():
    server = WireMockServer()
    try:
        server.start()
    except Exception:  # pragma: no cover - infrastructure guard
        pytest.skip("WireMock server not available in CI environment")
    
    # Configure wiremock client to use the server's port
    Config.base_url = f"http://localhost:{server.port}/__admin"
    
    # Reset any existing mappings using the client API
    mappings_client = Mappings()
    try:
        mappings_client.reset_mappings()
    except Exception:  # pragma: no cover - may not be available
        pass
    
    yield server
    server.stop()


def _register_mapping(server: WireMockServer, *, method: str, path: str, body: dict) -> None:
    mapping = Mapping(
        priority=1,
        request=MappingRequest(method=method, url=path),
        response=MappingResponse(
            status=200,
            json_body=body,
            headers={"Content-Type": "application/json"}
        ),
    )
    mappings_client = Mappings()
    mappings_client.create_mapping(mapping)


@pytest.mark.asyncio
async def test_next_insurance_certificate_via_wiremock(wiremock_server: WireMockServer) -> None:
    policy_number = "NEXT-123"
    base_url = f"http://localhost:{wiremock_server.port}"
    _register_mapping(
        wiremock_server,
        method="GET",
        path=f"/policies/{policy_number}",
        body={
            "active": True,
            "coverage": {"general_liability": "1M"},
            "effective_date": "2024-01-01",
            "expiration_date": "2025-01-01",
        },
    )
    _register_mapping(
        wiremock_server,
        method="POST",
        path=f"/policies/{policy_number}/certificates",
        body={
            "certificate_url": "https://example.com/certs/next-123.pdf",
            "issued_at": "2024-06-01T12:00:00",
            "insured_name": "Prep Kitchen",
        },
    )

    client = NextInsuranceAPI(base_url=base_url, api_key="test-key")
    verification = await client.verify_policy(policy_number)
    assert verification.active is True
    assert verification.coverage["general_liability"] == "1M"

    certificate = await client.issue_certificate(policy_number, insured_name="Prep Kitchen")
    assert certificate.certificate_url.endswith("next-123.pdf")
    assert certificate.provider == "next"


@pytest.mark.asyncio
async def test_thimble_certificate_via_wiremock(wiremock_server: WireMockServer) -> None:
    policy_number = "THIM-987"
    base_url = f"http://localhost:{wiremock_server.port}"
    _register_mapping(
        wiremock_server,
        method="GET",
        path=f"/policies/{policy_number}",
        body={
            "active": True,
            "coverage": {"general_liability": "500k"},
            "effective_date": "2024-02-01",
            "expiration_date": "2024-12-01",
        },
    )
    _register_mapping(
        wiremock_server,
        method="POST",
        path=f"/policies/{policy_number}/certificates",
        body={
            "certificate_url": "https://example.com/certs/thim-987.pdf",
            "issued_at": "2024-06-05T08:00:00",
            "insured_name": "Prep Kitchen",
        },
    )

    client = ThimbleAPI(base_url=base_url, api_key="test-key")
    verification = await client.verify_policy(policy_number)
    assert verification.active is True

    certificate = await client.issue_certificate(policy_number, insured_name="Prep Kitchen")
    assert certificate.certificate_url.endswith("thim-987.pdf")
    assert certificate.provider == "thimble"
