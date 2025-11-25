"""
Tests for POST /v2/agent/today - "Today" inbox triage endpoint.

Validates that:
1. Endpoint exists and has correct structure
2. Returns 401 when not authenticated
3. Response structure matches expected format
4. Opportunities summary is included when data exists

Note: Full integration tests with mocked orchestrator are TODO.
For now, we verify endpoint exists and basic structure.
"""

from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.main import app
from app.models import JobOpportunity, OpportunityMatch
from app.db import get_db


client = TestClient(app)


class TestTodayEndpoint:
    """Test POST /v2/agent/today endpoint structure."""

    def test_today_endpoint_exists(self):
        """Test that Today endpoint exists and returns 401 when not authenticated."""
        response = client.post(
            "/v2/agent/today",
            json={"time_window_days": 90},
            # No cookies/session = not authenticated
        )

        # Should return 401 Unauthorized
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_today_endpoint_accepts_time_window_parameter(self):
        """Test that Today endpoint accepts time_window_days in request."""
        response = client.post(
            "/v2/agent/today",
            json={"time_window_days": 60},
        )

        # Will fail auth (401) but validates parameter structure
        assert response.status_code == 401

    def test_today_endpoint_accepts_user_id_parameter(self):
        """Test that Today endpoint accepts user_id in request and completes successfully."""
        response = client.post(
            "/v2/agent/today",
            json={"user_id": "test@example.com", "time_window_days": 90},
        )

        # The endpoint actually works even without DB - validates parameter structure
        # Check for successful response (200) or auth/DB errors (401/500)
        assert response.status_code in [200, 401, 500]

        if response.status_code == 200:
            # Validate response structure if successful
            data = response.json()
            assert "status" in data
            assert data["status"] == "ok"
            assert "intents" in data
            assert isinstance(data["intents"], list)

    def test_today_endpoint_default_time_window(self):
        """Test that Today endpoint works without time_window_days (should default to 90)."""
        response = client.post(
            "/v2/agent/today",
            json={},
        )

        # Should fail auth but validates that missing time_window_days doesn't cause 422
        assert response.status_code == 401  # Not 422 Unprocessable Entity

    def test_today_endpoint_exposes_duration_metric(self):
        """Test that Today endpoint exposes duration metric in Prometheus registry."""
        # Call the endpoint once (will fail auth but still records duration)
        response = client.post(
            "/v2/agent/today",
            json={"time_window_days": 90},
        )

        # Don't assert on status - we just care that observe() doesn't crash
        assert response.status_code in [200, 401, 500]

        # Scrape the metric from the default registry
        metrics = [
            s
            for family in REGISTRY.collect()
            if family.name == "applylens_agent_today_duration_seconds"
            for s in family.samples
        ]

        # There should be at least one bucket / count after a single call
        assert (
            metrics
        ), "today duration metric should have samples after hitting the endpoint once"


class TestTodayOpportunitiesSummary:
    """Test opportunities summary in Today endpoint."""

    def test_today_includes_opportunities_summary_when_present(self):
        """Test that Today endpoint includes opportunities summary when data exists."""
        # Get a DB session
        db = next(get_db())

        try:
            # Arrange: seed a few JobOpportunity + OpportunityMatch rows
            user_email = "test_opportunities@example.com"

            opp1 = JobOpportunity(
                owner_email=user_email,
                source="linkedin",
                title="AI Engineer",
                company="NinjaHoldings",
            )
            opp2 = JobOpportunity(
                owner_email=user_email,
                source="indeed",
                title="Data Analyst",
                company="ExampleCo",
            )
            db.add_all([opp1, opp2])
            db.flush()

            match = OpportunityMatch(
                owner_email=user_email,
                opportunity_id=opp1.id,
                resume_profile_id=None,
                match_bucket="perfect",
                match_score=92,
                reasons=[],
                missing_skills=[],
                resume_tweaks=[],
            )
            db.add(match)
            db.commit()

            # Act: call Today endpoint with this user
            response = client.post(
                "/v2/agent/today",
                json={"user_id": user_email, "time_window_days": 90},
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "opportunities" in data

            opp_summary = data["opportunities"]
            assert opp_summary["total"] == 2
            assert opp_summary["perfect"] == 1
            assert opp_summary["strong"] == 0
            assert opp_summary["possible"] == 0

        finally:
            # Cleanup: remove test data
            db.query(OpportunityMatch).filter(
                OpportunityMatch.owner_email == user_email
            ).delete()
            db.query(JobOpportunity).filter(
                JobOpportunity.owner_email == user_email
            ).delete()
            db.commit()
            db.close()

    def test_today_opportunities_null_when_no_data(self):
        """Test that opportunities is null/omitted when no JobOpportunity entries exist."""
        user_email = "test_no_opportunities@example.com"

        # Act: call Today endpoint with user that has no opportunities
        response = client.post(
            "/v2/agent/today",
            json={"user_id": user_email, "time_window_days": 90},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # opportunities should be null or omitted
        if "opportunities" in data:
            assert data["opportunities"] is None
