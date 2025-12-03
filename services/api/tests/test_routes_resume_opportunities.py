"""Smoke tests for resume and opportunities routes.

Guards against:
1. Route renames/removals that would break the frontend
2. Regression to async def handlers with sync SQLAlchemy (causes 500 errors)

NOTE: These tests require DATABASE_URL to be set. If running locally outside Docker,
set environment variable: DATABASE_URL=postgresql://user:pass@localhost:5432/testdb
"""

import pytest


@pytest.mark.asyncio
async def test_resume_current_route_exists(async_client):
    """Verify /api/resume/current route is handled by our router."""
    resp = await async_client.get("/api/resume/current")
    assert resp.status_code in (200, 401, 404)  # 401 = auth required, 404 = not found
    # assert it's handled by our router, not FastAPI default 404
    body = resp.json()
    assert not (isinstance(body, dict) and body.get("detail") == "Not Found")


@pytest.mark.asyncio
async def test_opportunities_route_exists(async_client):
    """Verify /api/opportunities route is handled by our router."""
    resp = await async_client.get("/api/opportunities")
    assert resp.status_code in (200, 401, 404)  # 401 = auth required, 404 = not found
    body = resp.json()
    assert not (isinstance(body, dict) and body.get("detail") == "Not Found")


# ============================================================================
# REGRESSION TESTS: Async/Sync Mismatch (Dec 2024)
# ============================================================================
# These tests prevent regression to async def handlers with sync SQLAlchemy.
# If someone "helpfully" converts routes back to async def, these tests fail.
# Root cause: FastAPI can't properly serialize responses from async handlers
# that only contain synchronous operations (no await).
# ============================================================================


@pytest.fixture
def test_user_email():
    """Test user email for authentication."""
    return "test@example.com"


@pytest.fixture
def auth_headers(test_user_email):
    """Headers for authenticated requests."""
    return {"X-User-Email": test_user_email}


@pytest.mark.asyncio
async def test_opportunities_smoke_no_500(async_client, auth_headers):
    """Verify /api/opportunities doesn't return 500 with auth.

    Regression test for async/sync mismatch causing 500 errors.
    If this fails with 500, check that list_opportunities is `def`, not `async def`.
    """
    resp = await async_client.get("/api/opportunities", headers=auth_headers)
    # Should be 200 (with data) or 401 (if auth fails), never 500
    assert resp.status_code != 500, f"Got 500 Internal Server Error: {resp.text}"
    assert resp.status_code in (200, 401)

    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, list), "Response should be a list of opportunities"


@pytest.mark.asyncio
async def test_resume_current_smoke_no_500(async_client, auth_headers):
    """Verify /api/resume/current doesn't return 500 with auth.

    Regression test for async/sync mismatch causing 500 errors.
    If this fails with 500, check that get_current_resume is `def`, not `async def`.
    """
    resp = await async_client.get("/api/resume/current", headers=auth_headers)
    # Should be 200 (with data/null) or 401 (if auth fails), never 500
    assert resp.status_code != 500, f"Got 500 Internal Server Error: {resp.text}"
    assert resp.status_code in (200, 401)

    # null or object are both fine, we just care it doesn't 500
    if resp.status_code == 200:
        data = resp.json()
        assert data is None or isinstance(
            data, dict
        ), "Response should be null or resume object"
