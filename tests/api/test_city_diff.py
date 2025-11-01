"""Integration tests for the city diff router."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.index import create_app


client = TestClient(
    create_app(include_full_router=False, include_legacy_mounts=False)
)


def test_versions_endpoint_lists_available_diffs() -> None:
    response = client.get("/city/diff/versions")
    assert response.status_code == 200
    body = response.json()
    assert "versions" in body
    assert body["versions"], "expected at least one diff version"

    entry = body["versions"][0]
    assert {"version", "released_at", "jurisdictions"}.issubset(entry)
    assert entry["jurisdictions"], "expected jurisdictions to be populated"


def test_version_endpoint_supports_etag_caching() -> None:
    versions = client.get("/city/diff/versions").json()["versions"]
    version_id = versions[0]["version"]

    first = client.get(f"/city/diff/{version_id}")
    assert first.status_code == 200
    etag = first.headers.get("ETag")
    assert etag
    payload = first.json()
    assert payload["version"] == version_id

    cached = client.get(f"/city/diff/{version_id}", headers={"If-None-Match": etag})
    assert cached.status_code == 304
    assert cached.headers.get("ETag") == etag


def test_city_version_endpoint_filters_by_city() -> None:
    versions = client.get("/city/diff/versions").json()["versions"]
    version_id = versions[0]["version"]
    city_slug = versions[0]["jurisdictions"][0]

    first = client.get(f"/city/diff/{version_id}/{city_slug}")
    assert first.status_code == 200
    etag = first.headers.get("ETag")
    assert etag
    payload = first.json()
    assert payload["version"] == version_id
    assert payload["city"] == city_slug

    cached = client.get(
        f"/city/diff/{version_id}/{city_slug}", headers={"If-None-Match": etag}
    )
    assert cached.status_code == 304
    assert cached.headers.get("ETag") == etag

