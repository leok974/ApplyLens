"""
Unit tests for basic health and search endpoint happy paths.
"""

import pytest


@pytest.mark.asyncio
async def test_health(async_client):
    """Test /healthz endpoint returns 200 OK."""
    r = await async_client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data or r.text == "OK"


@pytest.mark.asyncio
async def test_search_min(async_client):
    """Test /search endpoint with minimal params."""
    r = await async_client.get("/search/", params={"q": "test", "size": 1})
    # Should return 200 (with results) or 204 (no content)
    assert r.status_code in (200, 204)

    if r.status_code == 200:
        data = r.json()
        # Verify response structure (adjust to your actual API schema)
        assert "results" in data or "items" in data or isinstance(data, list)


@pytest.mark.asyncio
async def test_search_empty_query(async_client):
    """Test /search endpoint handles empty query gracefully."""
    r = await async_client.get("/search/", params={"q": "", "size": 1})
    # Should handle gracefully (either 200 with empty results, 204, or 400 bad request)
    assert r.status_code in (200, 204, 400, 422)
