from __future__ import annotations

from fastapi.testclient import TestClient

from api.index import create_app

client = TestClient(create_app())


def test_diff_endpoint_returns_payload() -> None:
    response = client.get("/city/diff/sf")
    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "san_francisco"
    assert "version" in data
    assert "changes" in data and isinstance(data["changes"], list)
    assert response.headers.get("ETag")
    assert response.headers.get("X-Prep-Diff-Version") == data["version"]


def test_diff_endpoint_honors_if_none_match() -> None:
    first = client.get("/city/diff/sf")
    etag = first.headers["ETag"]
    cached = client.get("/city/diff/sf", headers={"If-None-Match": etag})
    assert cached.status_code == 304
    assert cached.content == b""
