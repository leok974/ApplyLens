"""
Tests for interview prep agent endpoint.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.schemas_agent import (
    InterviewPrepRequest,
    InterviewPrepResponse,
)


@pytest.fixture
def mock_app():
    """Mock Application model."""
    app = MagicMock()
    app.id = 1
    app.company = "Acme Corp"
    app.role = "Senior Software Engineer"
    app.status = "interview"
    app.applied_at = datetime(2025, 11, 1)
    return app


@pytest.fixture
def mock_thread_data():
    """Mock email thread data."""
    return {
        "thread_id": "thread-123",
        "messages": [
            {
                "date": "2025-11-05",
                "from": "recruiter@acme.com",
                "subject": "Interview Scheduled",
                "body": "We'd like to schedule a Zoom interview for December 1st at 2pm.",
            }
        ],
    }


@pytest.fixture
def mock_interview_prep_response():
    """Mock interview prep response."""
    return {
        "company": "Acme Corp",
        "role": "Senior Software Engineer",
        "interview_status": "Scheduled",
        "interview_date": "2025-12-01T14:00:00Z",
        "interview_format": "Zoom",
        "timeline": [
            "Applied on Nov 1",
            "HR screen on Nov 5",
            "Interview scheduled for Dec 1",
        ],
        "sections": [
            {
                "title": "What to Review",
                "bullets": [
                    "Review job description and requirements",
                    "Research Acme Corp's recent products",
                    "Prepare STAR examples from your experience",
                ],
            },
            {
                "title": "Questions to Ask",
                "bullets": [
                    "What does the team structure look like?",
                    "What technologies does the team use?",
                    "What are the growth opportunities?",
                ],
            },
        ],
    }


class TestInterviewPrepEndpoint:
    """Test the /v2/agent/interview-prep endpoint."""

    @pytest.mark.asyncio
    async def test_interview_prep_returns_expected_schema(
        self,
        mock_app,
        mock_thread_data,
        mock_interview_prep_response,
        async_client,
        test_db,
    ):
        """Test that endpoint returns valid InterviewPrepResponse."""
        with patch(
            "app.agent.orchestrator.MailboxAgentOrchestrator.interview_prep"
        ) as mock_prep:
            mock_prep.return_value = InterviewPrepResponse(
                **mock_interview_prep_response
            )

            # Make request
            request_data = {
                "application_id": 1,
                "thread_id": "thread-123",
                "preview_only": True,
            }

            response = await async_client.post(
                "/v2/agent/interview-prep", json=request_data
            )

            assert response.status_code == 200
            data = response.json()

            # Verify schema
            assert data["company"] == "Acme Corp"
            assert data["role"] == "Senior Software Engineer"
            assert data["interview_status"] == "Scheduled"
            assert data["interview_format"] == "Zoom"
            assert len(data["timeline"]) == 3
            assert len(data["sections"]) == 2

            # Verify sections structure
            section = data["sections"][0]
            assert "title" in section
            assert "bullets" in section
            assert isinstance(section["bullets"], list)

    @pytest.mark.asyncio
    async def test_interview_prep_increments_metric(
        self, mock_interview_prep_response, async_client, test_db
    ):
        """Test that calling endpoint increments the metric counter."""
        with patch(
            "app.agent.orchestrator.MailboxAgentOrchestrator.interview_prep"
        ) as mock_prep:
            mock_prep.return_value = InterviewPrepResponse(
                **mock_interview_prep_response
            )

            with patch("app.routers.agent.INTERVIEW_PREP_REQUESTS") as mock_metric:
                request_data = {
                    "application_id": 1,
                    "preview_only": True,
                }

                await async_client.post("/v2/agent/interview-prep", json=request_data)

                # Verify metric was incremented
                mock_metric.labels.assert_called_once()
                mock_metric.labels.return_value.inc.assert_called_once()

    @pytest.mark.asyncio
    async def test_interview_prep_handles_missing_application(
        self, async_client, test_db
    ):
        """Test that endpoint handles missing application gracefully."""
        with patch(
            "app.agent.orchestrator.MailboxAgentOrchestrator.interview_prep"
        ) as mock_prep:
            mock_prep.side_effect = ValueError("Application 999 not found")

            request_data = {
                "application_id": 999,
                "preview_only": True,
            }

            response = await async_client.post(
                "/v2/agent/interview-prep", json=request_data
            )

            # Should return 400 for validation errors
            assert response.status_code == 400
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_interview_prep_without_thread_id(
        self, mock_interview_prep_response, async_client, test_db
    ):
        """Test that endpoint works without thread_id (loads all threads for app)."""
        with patch(
            "app.agent.orchestrator.MailboxAgentOrchestrator.interview_prep"
        ) as mock_prep:
            mock_prep.return_value = InterviewPrepResponse(
                **mock_interview_prep_response
            )

            request_data = {
                "application_id": 1,
                "preview_only": True,
                # No thread_id
            }

            response = await async_client.post(
                "/v2/agent/interview-prep", json=request_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["company"] == "Acme Corp"


class TestInterviewPrepOrchestrator:
    """Test the orchestrator interview_prep method."""

    @pytest.mark.asyncio
    async def test_orchestrator_loads_application(
        self, mock_app, mock_thread_data, test_db
    ):
        """Test that orchestrator loads application correctly."""
        from app.agent.orchestrator import MailboxAgentOrchestrator
        from app.config import RequestContext

        ctx = RequestContext(user_id="test@example.com", db_session=test_db)
        orchestrator = MailboxAgentOrchestrator(ctx=ctx)

        with (
            patch.object(test_db, "execute") as mock_execute,
            patch("app.agent.orchestrator.GmailService") as mock_gmail_class,
            patch.object(orchestrator, "_call_llm_for_interview_prep") as mock_llm,
        ):
            # Mock database query to return application
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_app
            mock_execute.return_value = mock_result

            # Mock Gmail service
            mock_gmail = AsyncMock()
            mock_gmail.get_thread.return_value = mock_thread_data
            mock_gmail_class.return_value = mock_gmail

            # Mock LLM response
            mock_llm.return_value = {
                "company": "Acme Corp",
                "role": "Senior Software Engineer",
                "timeline": ["Applied on Nov 1"],
                "sections": [
                    {"title": "Preparation", "bullets": ["Review job description"]}
                ],
            }

            # Call method
            request = InterviewPrepRequest(application_id=1, thread_id="thread-123")
            response = await orchestrator.interview_prep(request)

            # Verify response
            assert response.company == "Acme Corp"
            assert response.role == "Senior Software Engineer"
            assert len(response.timeline) >= 1
            assert len(response.sections) >= 1

    @pytest.mark.asyncio
    async def test_orchestrator_handles_llm_failure_gracefully(self, mock_app, test_db):
        """Test that orchestrator returns fallback response on LLM failure."""
        from app.agent.orchestrator import MailboxAgentOrchestrator
        from app.config import RequestContext

        ctx = RequestContext(user_id="test@example.com", db_session=test_db)
        orchestrator = MailboxAgentOrchestrator(ctx=ctx)

        with (
            patch.object(test_db, "execute") as mock_execute,
            patch("app.agent.orchestrator.GmailService") as mock_gmail_class,
            patch.object(orchestrator, "_call_llm_for_interview_prep") as mock_llm,
        ):
            # Mock database query
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_app
            mock_execute.return_value = mock_result

            # Mock Gmail service
            mock_gmail = AsyncMock()
            mock_gmail.get_thread.return_value = None
            mock_gmail_class.return_value = mock_gmail

            # Mock LLM to raise exception
            mock_llm.side_effect = Exception("LLM service unavailable")

            # Call method - should not raise, returns fallback
            request = InterviewPrepRequest(application_id=1)
            response = await orchestrator.interview_prep(request)

            # Verify fallback response
            assert response.company == "Acme Corp"
            assert response.role == "Senior Software Engineer"
            assert len(response.sections) > 0
            assert "Preparation" in response.sections[0].title
