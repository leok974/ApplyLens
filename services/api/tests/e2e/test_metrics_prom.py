"""
E2E tests for Prometheus metrics endpoint (/metrics).

Tests the backfill health metrics without requiring a real Elasticsearch cluster.
"""

import sys
from pathlib import Path

import pytest
from httpx import AsyncClient

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import validate_backfill as V  # noqa: E402

from app.main import app  # noqa: E402


class FakeES:
    """Mock Elasticsearch client for testing metrics."""

    def count(self, index, body):
        """Mock count() method that returns different values based on query structure."""
        query = body["query"]
        bool_query = query.get("bool", {})

        # Detect query type by checking for exists/must_not clauses
        filters = bool_query.get("filter", [])
        must_not = bool_query.get("must_not", [])

        # Check for specific field existence checks
        has_dates = {"exists": {"field": "dates"}} in filters
        has_exp = {"exists": {"field": "expires_at"}} in filters
        missing = {"exists": {"field": "dates"}} in must_not

        # Return counts based on query type
        if missing:
            # Bills missing dates
            return {"count": 2}
        elif has_dates and has_exp:
            # Bills with both dates and expires_at
            return {"count": 18}
        elif has_dates:
            # Bills with dates (any)
            return {"count": 20}

        return {"count": 0}


@pytest.mark.asyncio
async def test_metrics_endpoint(monkeypatch):
    """
    Test that /metrics endpoint returns Prometheus metrics with expected values.

    Scenario:
    - 2 bills missing dates
    - 20 bills with dates
    - 18 bills with expires_at
    """
    # Import app here to avoid circular imports

    # Mock the ES client
    monkeypatch.setattr(V, "es", lambda: FakeES())

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/metrics")

        assert response.status_code == 200

        body = response.text

        # Check that metric names are present
        assert "bills_missing_dates" in body
        assert "bills_with_dates" in body
        assert "bills_with_expires_at" in body
        assert "backfill_health_last_run_timestamp" in body
        assert "backfill_health_index_info" in body

        # Check numeric values (Prometheus format uses .0 for floats)
        assert "bills_missing_dates 2.0" in body
        assert "bills_with_dates 20.0" in body
        assert "bills_with_expires_at 18.0" in body


@pytest.mark.asyncio
async def test_metrics_refresh_endpoint(monkeypatch):
    """
    Test that POST /metrics/refresh endpoint triggers metrics refresh.

    This is useful for precomputing metrics on a schedule instead of
    refreshing on every scrape.
    """

    # Mock the ES client
    monkeypatch.setattr(V, "es", lambda: FakeES())

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/metrics/refresh")

        assert response.status_code == 200
        assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_metrics_content_type(monkeypatch):
    """Test that /metrics endpoint returns correct Prometheus content type."""

    monkeypatch.setattr(V, "es", lambda: FakeES())

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/metrics")

        assert response.status_code == 200

        # Prometheus metrics should use specific content type
        content_type = response.headers.get("content-type", "")
        assert (
            "text/plain" in content_type
            or "application/openmetrics-text" in content_type
        )


@pytest.mark.asyncio
async def test_metrics_zero_missing(monkeypatch):
    """
    Test metrics when backfill is perfect (no missing dates).

    Scenario:
    - 0 bills missing dates
    - 100 bills with dates
    - 100 bills with expires_at (100% coverage)
    """

    class PerfectES:
        """ES client that returns perfect backfill results."""

        def count(self, index, body):
            query = body["query"]
            bool_query = query.get("bool", {})
            filters = bool_query.get("filter", [])
            must_not = bool_query.get("must_not", [])

            has_dates = {"exists": {"field": "dates"}} in filters
            has_exp = {"exists": {"field": "expires_at"}} in filters
            missing = {"exists": {"field": "dates"}} in must_not

            if missing:
                return {"count": 0}  # No missing dates
            elif has_dates and has_exp:
                return {"count": 100}  # All have expires_at
            elif has_dates:
                return {"count": 100}  # All have dates

            return {"count": 0}

    monkeypatch.setattr(V, "es", lambda: PerfectES())

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/metrics")

        assert response.status_code == 200
        body = response.text

        # Perfect backfill scenario
        assert "bills_missing_dates 0.0" in body
        assert "bills_with_dates 100.0" in body
        assert "bills_with_expires_at 100.0" in body
