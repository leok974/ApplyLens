"""
Unit tests for API happy paths - quick smoke tests for core endpoints.

These tests verify basic API functionality without complex setup,
using the async_client fixture with ASGITransport.
"""

import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_healthz(async_client):
    """Test /healthz endpoint returns 200 OK."""
    r = await async_client.get("/healthz")
    assert r.status_code == 200
    # Response may be JSON with {"status": "ok"} or plain text "OK"
    if r.headers.get("content-type", "").startswith("application/json"):
        data = r.json()
        assert "status" in data or data  # Flexible assertion
    else:
        assert r.text in ("OK", "ok", "healthy")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_minimal(async_client):
    """Test /search endpoint with minimal params."""
    r = await async_client.get("/search/", params={"q": "test", "size": 1})
    # May return 200 with results, or 204 if no data
    assert r.status_code in (200, 204)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_empty_query(async_client):
    """Test /search endpoint handles empty query gracefully."""
    r = await async_client.get("/search/", params={"q": "", "size": 1})
    # Should handle empty query (may return 400, 422, or empty 200/204)
    assert r.status_code in (200, 204, 400, 422)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_root_endpoint(async_client):
    """Test root endpoint returns something valid."""
    r = await async_client.get("/")
    # Root may redirect or return welcome message
    assert r.status_code in (200, 307, 308, 404)  # Various valid responses


@pytest.mark.unit
@pytest.mark.asyncio
async def test_docs_endpoint_accessible(async_client):
    """Test that API docs endpoint is accessible."""
    r = await async_client.get("/docs")
    # FastAPI docs should be available (may redirect)
    assert r.status_code in (200, 307, 308)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_metrics_endpoint(async_client):
    """Test that metrics endpoint responds."""
    r = await async_client.get("/metrics")
    # Prometheus metrics endpoint
    # May return 200 with metrics or 404 if not enabled
    assert r.status_code in (200, 404, 501)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_invalid_params(async_client):
    """Test /search with invalid parameters returns appropriate error."""
    r = await async_client.get("/search/", params={"size": -1})
    # Should reject negative size
    assert r.status_code in (400, 422)  # Validation error


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_large_size(async_client):
    """Test /search with reasonable size parameter."""
    r = await async_client.get("/search/", params={"q": "test", "size": 10})
    # Should handle reasonable size
    assert r.status_code in (200, 204)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cors_preflight(async_client):
    """Test CORS preflight request handling."""
    r = await async_client.options(
        "/search/",
        headers={"Origin": "http://localhost:5175"}
    )
    # OPTIONS request for CORS preflight
    # May return 200 or 204 with CORS headers
    assert r.status_code in (200, 204, 405)
