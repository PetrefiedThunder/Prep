"""API tests for the city fee summary endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.index import create_app

client = TestClient(
    create_app(include_full_router=False, include_legacy_mounts=False)
)


def test_summary_basic():
    response = client.get("/city/sf/fees/summary")
    assert response.status_code == 200
    body = response.json()
    assert "jurisdiction" in body
    assert "totals" in body
    assert "validation" in body
    assert "ETag" in response.headers


def test_summary_etag_304():
    first = client.get("/city/oakland/fees/summary")
    etag = first.headers.get("ETag")
    assert etag

    second = client.get("/city/oakland/fees/summary", headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second.headers.get("ETag") == etag
