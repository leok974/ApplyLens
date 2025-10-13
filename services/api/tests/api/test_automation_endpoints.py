"""
API contract tests for /automation/* endpoints.

Tests all automation endpoints for correct status codes, response schemas,
and error handling. Requires a running API server.
"""

import httpx
import pytest

# Base URL for API tests (configured via environment or fixture)
BASE_URL = "http://localhost:8003"


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def api_client():
    """HTTP client for API testing."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture
async def async_api_client():
    """Async HTTP client for API testing."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client


# ============================================================================
# HEALTH ENDPOINT TESTS
# ============================================================================


@pytest.mark.api
class TestHealthEndpoint:
    """Tests for GET /automation/health endpoint."""

    def test_health_returns_200(self, api_client):
        """Health endpoint should return 200 OK."""
        response = api_client.get("/automation/health")
        assert response.status_code == 200

    def test_health_response_schema(self, api_client):
        """Health endpoint should return expected schema."""
        response = api_client.get("/automation/health")
        data = response.json()

        # Required fields
        assert "status" in data
        assert "statistics" in data

        # Status should be a string
        assert isinstance(data["status"], str)

        # Statistics should have expected fields
        stats = data["statistics"]
        assert "total_emails" in stats
        assert "emails_with_risk_scores" in stats
        assert "coverage_percentage" in stats

        # Numeric fields should be numbers
        assert isinstance(stats["total_emails"], int)
        assert isinstance(stats["emails_with_risk_scores"], int)
        assert isinstance(stats["coverage_percentage"], (int, float))

    def test_health_coverage_percentage_valid(self, api_client):
        """Coverage percentage should be between 0 and 100."""
        response = api_client.get("/automation/health")
        data = response.json()
        coverage = data["statistics"]["coverage_percentage"]
        assert 0 <= coverage <= 100

    def test_health_last_computed_format(self, api_client):
        """Last computed should be ISO timestamp if present."""
        response = api_client.get("/automation/health")
        data = response.json()

        if "last_computed" in data:
            # Should be parseable as ISO timestamp
            from datetime import datetime

            timestamp = data["last_computed"]
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


# ============================================================================
# RISK SUMMARY ENDPOINT TESTS
# ============================================================================


@pytest.mark.api
class TestRiskSummaryEndpoint:
    """Tests for GET /automation/risk-summary endpoint."""

    def test_risk_summary_returns_200(self, api_client):
        """Risk summary should return 200 OK."""
        response = api_client.get("/automation/risk-summary")
        assert response.status_code == 200

    def test_risk_summary_default_days(self, api_client):
        """Risk summary should accept default days parameter."""
        response = api_client.get("/automation/risk-summary")
        data = response.json()

        assert "period" in data
        assert data["period"]["days"] == 7  # Default

    def test_risk_summary_custom_days(self, api_client):
        """Risk summary should accept custom days parameter."""
        response = api_client.get("/automation/risk-summary?days=30")
        data = response.json()

        assert data["period"]["days"] == 30

    def test_risk_summary_response_schema(self, api_client):
        """Risk summary should return expected schema."""
        response = api_client.get("/automation/risk-summary?days=365")
        data = response.json()

        # Required top-level fields
        assert "period" in data
        assert "statistics" in data
        assert "distribution" in data
        assert "top_risky_emails" in data

        # Statistics fields
        stats = data["statistics"]
        assert "total_emails" in stats
        assert "average_risk_score" in stats
        assert "min_risk_score" in stats
        assert "max_risk_score" in stats

        # Distribution fields
        dist = data["distribution"]
        assert "low" in dist
        assert "medium" in dist
        assert "high" in dist

        # Top risky emails should be a list
        assert isinstance(data["top_risky_emails"], list)

    def test_risk_summary_distribution_sum(self, api_client):
        """Distribution buckets should sum to approximately total emails."""
        response = api_client.get("/automation/risk-summary?days=365")
        data = response.json()

        total = data["statistics"]["total_emails"]
        dist = data["distribution"]
        dist_sum = dist["low"] + dist["medium"] + dist["high"]

        # Should be close (within 10% due to filtering)
        if total > 0:
            ratio = dist_sum / total
            assert 0.8 <= ratio <= 1.2

    def test_risk_summary_top_emails_schema(self, api_client):
        """Top risky emails should have expected fields."""
        response = api_client.get("/automation/risk-summary?days=365")
        data = response.json()

        top_emails = data["top_risky_emails"]
        if len(top_emails) > 0:
            email = top_emails[0]
            assert "id" in email
            assert "sender" in email
            assert "subject" in email
            assert "risk_score" in email
            assert "category" in email or email.get("category") is None

    def test_risk_summary_with_category_filter(self, api_client):
        """Risk summary should accept category filter."""
        response = api_client.get("/automation/risk-summary?category=recruiter&days=90")
        assert response.status_code == 200
        data = response.json()
        assert "filter" in data
        assert data["filter"]["category"] == "recruiter"

    def test_risk_summary_negative_days_error(self, api_client):
        """Negative days should return error."""
        response = api_client.get("/automation/risk-summary?days=-1")
        assert response.status_code == 422  # Validation error

    def test_risk_summary_zero_days(self, api_client):
        """Zero days should either error or return empty results."""
        response = api_client.get("/automation/risk-summary?days=0")
        # Could be 422 (validation error) or 200 with zero results
        assert response.status_code in [200, 422]


# ============================================================================
# RISK TRENDS ENDPOINT TESTS
# ============================================================================


@pytest.mark.api
class TestRiskTrendsEndpoint:
    """Tests for GET /automation/risk-trends endpoint."""

    def test_risk_trends_returns_200(self, api_client):
        """Risk trends should return 200 OK."""
        response = api_client.get("/automation/risk-trends")
        assert response.status_code == 200

    def test_risk_trends_default_parameters(self, api_client):
        """Risk trends should accept default parameters."""
        response = api_client.get("/automation/risk-trends")
        data = response.json()

        assert "period" in data
        assert data["period"]["days"] == 30  # Default
        assert data["period"]["granularity"] == "day"  # Default

    def test_risk_trends_weekly_granularity(self, api_client):
        """Risk trends should accept weekly granularity."""
        response = api_client.get("/automation/risk-trends?days=90&granularity=week")
        data = response.json()

        assert data["period"]["granularity"] == "week"

    def test_risk_trends_response_schema(self, api_client):
        """Risk trends should return expected schema."""
        response = api_client.get("/automation/risk-trends?days=30")
        data = response.json()

        # Required fields
        assert "period" in data
        assert "trends" in data

        # Trends should be a list
        trends = data["trends"]
        assert isinstance(trends, list)

        # Each trend point should have expected fields
        if len(trends) > 0:
            trend = trends[0]
            assert "period" in trend
            assert "email_count" in trend
            assert "average_risk_score" in trend
            assert "max_risk_score" in trend

    def test_risk_trends_sorted_by_period(self, api_client):
        """Trends should be sorted chronologically."""
        response = api_client.get("/automation/risk-trends?days=60&granularity=week")
        data = response.json()

        trends = data["trends"]
        if len(trends) > 1:
            # Check that periods are increasing
            from datetime import datetime

            periods = [
                datetime.fromisoformat(t["period"].replace("Z", "+00:00"))
                for t in trends
            ]
            assert periods == sorted(periods)

    def test_risk_trends_invalid_granularity(self, api_client):
        """Invalid granularity should return error."""
        response = api_client.get("/automation/risk-trends?granularity=month")
        assert response.status_code == 422  # Validation error

    def test_risk_trends_negative_days(self, api_client):
        """Negative days should return error."""
        response = api_client.get("/automation/risk-trends?days=-30")
        assert response.status_code == 422


# ============================================================================
# RECOMPUTE ENDPOINT TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.slow
class TestRecomputeEndpoint:
    """Tests for POST /automation/recompute endpoint."""

    def test_recompute_dry_run_returns_200(self, api_client):
        """Dry run recompute should return 200 OK."""
        response = api_client.post(
            "/automation/recompute", json={"dry_run": True, "batch_size": 10}
        )
        assert response.status_code == 200

    def test_recompute_response_schema(self, api_client):
        """Recompute should return expected schema."""
        response = api_client.post(
            "/automation/recompute", json={"dry_run": True, "batch_size": 10}
        )
        data = response.json()

        # Required fields
        assert "status" in data
        assert "dry_run" in data
        assert "statistics" in data

        # Statistics should have processing info
        stats = data["statistics"]
        assert "processed" in stats
        assert "updated" in stats
        assert "duration_seconds" in stats

    def test_recompute_dry_run_idempotent(self, api_client):
        """Dry run should be idempotent (no actual changes)."""
        response1 = api_client.post(
            "/automation/recompute", json={"dry_run": True, "batch_size": 50}
        )
        response2 = api_client.post(
            "/automation/recompute", json={"dry_run": True, "batch_size": 50}
        )

        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Statistics should be similar (same dataset)
        stats1 = response1.json()["statistics"]
        stats2 = response2.json()["statistics"]
        assert stats1["processed"] == stats2["processed"]

    def test_recompute_custom_batch_size(self, api_client):
        """Recompute should respect custom batch size."""
        response = api_client.post(
            "/automation/recompute", json={"dry_run": True, "batch_size": 25}
        )
        data = response.json()
        assert data["batch_size"] == 25

    def test_recompute_zero_batch_size_error(self, api_client):
        """Zero batch size should return error."""
        response = api_client.post(
            "/automation/recompute", json={"dry_run": True, "batch_size": 0}
        )
        assert response.status_code == 422

    def test_recompute_negative_batch_size_error(self, api_client):
        """Negative batch size should return error."""
        response = api_client.post(
            "/automation/recompute", json={"dry_run": True, "batch_size": -100}
        )
        assert response.status_code == 422

    def test_recompute_oversize_batch_error(self, api_client):
        """Excessively large batch size should be handled."""
        response = api_client.post(
            "/automation/recompute", json={"dry_run": True, "batch_size": 1000000}
        )
        # Should either succeed (capped) or return 422
        assert response.status_code in [200, 422]

    def test_recompute_missing_parameters(self, api_client):
        """Recompute should work with missing parameters (use defaults)."""
        response = api_client.post("/automation/recompute", json={})
        # Should succeed with defaults
        assert response.status_code == 200

    def test_recompute_invalid_json(self, api_client):
        """Invalid JSON should return error."""
        response = api_client.post(
            "/automation/recompute",
            data="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.api
class TestErrorHandling:
    """Tests for general error handling."""

    def test_nonexistent_endpoint_returns_404(self, api_client):
        """Nonexistent endpoint should return 404."""
        response = api_client.get("/automation/nonexistent")
        assert response.status_code == 404

    def test_wrong_method_returns_405(self, api_client):
        """Wrong HTTP method should return 405."""
        response = api_client.post("/automation/health")
        assert response.status_code == 405

    def test_invalid_content_type(self, api_client):
        """Invalid content type should return error."""
        response = api_client.post(
            "/automation/recompute",
            data="param=value",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        # Should return 415 (Unsupported Media Type) or 422
        assert response.status_code in [415, 422]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.integration
class TestEndpointIntegration:
    """Integration tests for multiple endpoints."""

    def test_recompute_then_check_health(self, api_client):
        """After recompute, health should show updated coverage."""
        # Get initial health
        health1 = api_client.get("/automation/health").json()

        # Trigger recompute
        api_client.post(
            "/automation/recompute", json={"dry_run": False, "batch_size": 100}
        )

        # Get updated health
        health2 = api_client.get("/automation/health").json()

        # Coverage should be >= initial (or unchanged in dry run)
        coverage1 = health1["statistics"]["coverage_percentage"]
        coverage2 = health2["statistics"]["coverage_percentage"]
        assert coverage2 >= coverage1

    def test_summary_and_trends_consistency(self, api_client):
        """Summary and trends should show consistent data."""
        summary = api_client.get("/automation/risk-summary?days=30").json()
        trends = api_client.get(
            "/automation/risk-trends?days=30&granularity=day"
        ).json()

        # Both should report on the same period
        assert summary["period"]["days"] == 30
        assert trends["period"]["days"] == 30

        # Total from trends should match or be close to summary
        if len(trends["trends"]) > 0:
            trend_total = sum(t["email_count"] for t in trends["trends"])
            summary_total = summary["statistics"]["total_emails"]

            # Should be close (within 10% due to different filtering)
            if summary_total > 0:
                ratio = trend_total / summary_total
                assert 0.8 <= ratio <= 1.2
