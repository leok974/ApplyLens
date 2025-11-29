"""Smoke tests for resume and opportunities routes.

Guards against route renames/removals that would break the frontend.

NOTE: These tests require DATABASE_URL to be set. If running locally outside Docker,
set environment variable: DATABASE_URL=postgresql://user:pass@localhost:5432/testdb
"""

import pytest


@pytest.mark.asyncio
async def test_resume_current_route_exists(async_client):
    """Verify /api/resume/current route is handled by our router."""
    resp = await async_client.get("/api/resume/current")
    assert resp.status_code in (200, 404)
    # assert it's handled by our router, not FastAPI default 404
    body = resp.json()
    assert not (isinstance(body, dict) and body.get("detail") == "Not Found")


@pytest.mark.asyncio
async def test_opportunities_route_exists(async_client):
    """Verify /api/opportunities route is handled by our router."""
    resp = await async_client.get("/api/opportunities")
    assert resp.status_code in (200, 404)
    body = resp.json()
    assert not (isinstance(body, dict) and body.get("detail") == "Not Found")
