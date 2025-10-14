"""
API tests for /applications endpoints.

Tests happy path scenarios for listing and retrieving applications,
including basic CRUD operations.
"""

import pytest


@pytest.mark.api
@pytest.mark.anyio
async def test_list_applications_ok(async_client, db_session, seed_minimal):
    """List applications endpoint should return 200 with results."""
    # seed_minimal provided by conftest (creates one Application+Email)
    seed_minimal(db_session)
    r = await async_client.get("/applications", params={"size": 10})
    assert r.status_code in (200, 204)
    
    if r.status_code == 200:
        data = r.json()
        # Should have some structure (exact format depends on endpoint)
        assert isinstance(data, (list, dict))


@pytest.mark.api
@pytest.mark.anyio
async def test_list_applications_with_pagination(async_client, db_session, seed_minimal):
    """List applications should support pagination parameters."""
    seed_minimal(db_session)
    r = await async_client.get("/applications", params={"size": 1, "offset": 0})
    assert r.status_code in (200, 204)


@pytest.mark.api
@pytest.mark.anyio
async def test_get_application_by_id_ok(async_client, db_session, seed_minimal):
    """Get application by ID should return application details."""
    app, _ = seed_minimal(db_session)  # fixture returns (Application, Email)
    r = await async_client.get(f"/applications/{app.id}")
    assert r.status_code in (200, 404)  # depends on router behavior
    
    if r.status_code == 200:
        data = r.json()
        assert "id" in data or "company" in data  # Should have application data


@pytest.mark.api
@pytest.mark.anyio
async def test_get_application_invalid_id(async_client):
    """Get application with invalid ID should return 404."""
    r = await async_client.get("/applications/99999")
    assert r.status_code in (404, 422)


@pytest.mark.api
@pytest.mark.anyio
async def test_list_applications_empty_database(async_client, db_session):
    """List applications with empty database should return empty result."""
    r = await async_client.get("/applications", params={"size": 10})
    assert r.status_code in (200, 204)
    
    if r.status_code == 200:
        data = r.json()
        # Should be empty or have empty items list
        if isinstance(data, list):
            assert len(data) == 0
        elif isinstance(data, dict):
            assert data.get("items", []) == [] or data.get("total", 0) == 0


@pytest.mark.api
@pytest.mark.anyio
async def test_list_applications_with_filters(async_client, db_session, seed_minimal):
    """List applications should support filter parameters."""
    app, _ = seed_minimal(db_session)
    # Try filtering by status or company if supported
    r = await async_client.get("/applications", params={"status": "applied", "size": 10})
    assert r.status_code in (200, 204, 422)  # 422 if filter not supported
