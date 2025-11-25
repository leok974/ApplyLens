"""
Tests for follow-up draft email generation endpoint.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.schemas_agent import FollowupDraftRequest, FollowupDraftResponse, FollowupDraft
from app.models import Application, AppStatus


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock(spec=Session)
    return session


@pytest.fixture
def mock_application():
    """Mock Application object."""
    app = MagicMock(spec=Application)
    app.id = 1
    app.company = "Test Corp"
    app.role = "Software Engineer"
    app.status = AppStatus.APPLIED
    app.notes = "Great opportunity"
    return app


@pytest.fixture
def mock_thread_detail_result():
    """Mock thread_detail tool result."""
    return {
        "messages": [
            {
                "from": "recruiter@testcorp.com",
                "date": "2024-01-15T10:00:00Z",
                "subject": "Software Engineer Opportunity",
                "body": "We'd like to discuss the Software Engineer role with you. Are you available for a call this week?",
            },
            {
                "from": "me@example.com",
                "date": "2024-01-15T14:30:00Z",
                "subject": "Re: Software Engineer Opportunity",
                "body": "Thanks for reaching out! I'm very interested. I'm available Tuesday or Thursday afternoon.",
            },
        ]
    }


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for draft generation."""
    return {
        "subject": "Following Up on Software Engineer Role",
        "body": "Hi,\n\nI wanted to follow up on our conversation about the Software Engineer position at Test Corp. I remain very interested in this opportunity and would love to hear about next steps.\n\nPlease let me know if you need any additional information from me.\n\nBest regards",
    }


class TestFollowupDraftEndpoint:
    """Test cases for /v2/agent/followup-draft endpoint."""

    def test_draft_followup_success(
        self,
        mock_db_session,
        mock_application,
        mock_thread_detail_result,
        mock_llm_response,
    ):
        """Test successful draft generation with all context."""
        client = TestClient(app)

        # Mock dependencies
        with (
            patch("app.routers.agent.get_db") as mock_get_db,
            patch("app.routers.agent.get_orchestrator") as mock_get_orch,
            patch("app.routers.agent.FOLLOWUP_DRAFT_REQUESTS") as mock_metric,
        ):
            # Setup mocks
            mock_get_db.return_value = mock_db_session
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_application

            mock_orchestrator = MagicMock()
            mock_orchestrator.draft_followup = AsyncMock(
                return_value=FollowupDraftResponse(
                    status="ok",
                    draft=FollowupDraft(
                        subject=mock_llm_response["subject"],
                        body=mock_llm_response["body"],
                    ),
                )
            )
            mock_get_orch.return_value = mock_orchestrator

            # Make request with session user_id
            with client.websocket_connect("/ws") as _:
                pass  # Establish session

            # In actual test, we'd need to set up proper auth
            # For now, test the schema validation
            payload = {
                "user_id": "test-user-123",
                "thread_id": "thread-456",
                "application_id": 1,
                "mode": "preview_only",
            }

            response = client.post("/v2/agent/followup-draft", json=payload)

            # Should record metric
            mock_metric.labels.assert_called_once_with(source="thread_viewer")
            mock_metric.labels.return_value.inc.assert_called_once()

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "draft" in data
            assert data["draft"]["subject"] == mock_llm_response["subject"]
            assert data["draft"]["body"] == mock_llm_response["body"]

    def test_draft_followup_missing_thread_id(self):
        """Test request with missing thread_id returns 422."""
        client = TestClient(app)

        payload = {
            "user_id": "test-user-123",
            # Missing thread_id
            "mode": "preview_only",
        }

        response = client.post("/v2/agent/followup-draft", json=payload)
        assert response.status_code == 422  # Validation error

    def test_draft_followup_invalid_mode(self):
        """Test request with invalid mode returns 422."""
        client = TestClient(app)

        payload = {
            "user_id": "test-user-123",
            "thread_id": "thread-456",
            "mode": "invalid_mode",  # Not a valid Literal value
        }

        response = client.post("/v2/agent/followup-draft", json=payload)
        assert response.status_code == 422

    def test_draft_followup_orchestrator_error(self, mock_db_session):
        """Test handling of orchestrator errors."""
        client = TestClient(app)

        with (
            patch("app.routers.agent.get_db") as mock_get_db,
            patch("app.routers.agent.get_orchestrator") as mock_get_orch,
        ):
            mock_get_db.return_value = mock_db_session

            # Orchestrator returns error response
            mock_orchestrator = MagicMock()
            mock_orchestrator.draft_followup = AsyncMock(
                return_value=FollowupDraftResponse(
                    status="error", message="Failed to retrieve thread details"
                )
            )
            mock_get_orch.return_value = mock_orchestrator

            payload = {
                "user_id": "test-user-123",
                "thread_id": "invalid-thread",
                "mode": "preview_only",
            }

            response = client.post("/v2/agent/followup-draft", json=payload)

            # Should still return 200 but with error status
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "message" in data
            assert "Failed to retrieve thread details" in data["message"]

    def test_draft_followup_without_application_context(
        self, mock_db_session, mock_thread_detail_result, mock_llm_response
    ):
        """Test draft generation without application context."""
        client = TestClient(app)

        with (
            patch("app.routers.agent.get_db") as mock_get_db,
            patch("app.routers.agent.get_orchestrator") as mock_get_orch,
        ):
            mock_get_db.return_value = mock_db_session

            mock_orchestrator = MagicMock()
            mock_orchestrator.draft_followup = AsyncMock(
                return_value=FollowupDraftResponse(
                    status="ok",
                    draft=FollowupDraft(
                        subject="Following Up",
                        body="I wanted to check in on the status of my application.",
                    ),
                )
            )
            mock_get_orch.return_value = mock_orchestrator

            # No application_id provided
            payload = {
                "user_id": "test-user-123",
                "thread_id": "thread-456",
                "mode": "preview_only",
            }

            response = client.post("/v2/agent/followup-draft", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "draft" in data


class TestOrchestratorDraftFollowup:
    """Test cases for orchestrator.draft_followup method."""

    @pytest.mark.asyncio
    async def test_draft_followup_tool_execution(
        self, mock_db_session, mock_thread_detail_result
    ):
        """Test that draft_followup correctly calls thread_detail tool."""
        from app.agent.orchestrator import MailboxAgentOrchestrator
        from app.agent.tools import ToolRegistry

        # Mock tool registry
        mock_tool_result = MagicMock()
        mock_tool_result.data = mock_thread_detail_result

        mock_registry = MagicMock(spec=ToolRegistry)
        mock_registry.execute = AsyncMock(return_value=mock_tool_result)

        orchestrator = MailboxAgentOrchestrator(
            tool_registry=mock_registry,
            enable_llm_fallback=True,
        )

        # Mock LLM call
        with patch.object(
            orchestrator,
            "_call_llm_for_draft",
            new=AsyncMock(
                return_value={"subject": "Test Subject", "body": "Test Body"}
            ),
        ):
            request = FollowupDraftRequest(
                user_id="test-user", thread_id="thread-123", mode="preview_only"
            )

            result = await orchestrator.draft_followup(request, mock_db_session)

            # Verify tool was called correctly
            mock_registry.execute.assert_called_once_with(
                "thread_detail", {"thread_id": "thread-123"}, "test-user"
            )

            # Verify successful response
            assert result.status == "ok"
            assert result.draft is not None
            assert result.draft.subject == "Test Subject"
            assert result.draft.body == "Test Body"

    @pytest.mark.asyncio
    async def test_draft_followup_empty_thread(self, mock_db_session):
        """Test handling of empty thread."""
        from app.agent.orchestrator import MailboxAgentOrchestrator
        from app.agent.tools import ToolRegistry

        # Mock tool registry returning empty messages
        mock_tool_result = MagicMock()
        mock_tool_result.data = {"messages": []}

        mock_registry = MagicMock(spec=ToolRegistry)
        mock_registry.execute = AsyncMock(return_value=mock_tool_result)

        orchestrator = MailboxAgentOrchestrator(
            tool_registry=mock_registry,
            enable_llm_fallback=True,
        )

        request = FollowupDraftRequest(
            user_id="test-user", thread_id="empty-thread", mode="preview_only"
        )

        result = await orchestrator.draft_followup(request, mock_db_session)

        # Should return error for empty thread
        assert result.status == "error"
        assert "No messages found" in result.message

    @pytest.mark.asyncio
    async def test_draft_followup_llm_failure(
        self, mock_db_session, mock_thread_detail_result
    ):
        """Test handling of LLM generation failure."""
        from app.agent.orchestrator import MailboxAgentOrchestrator
        from app.agent.tools import ToolRegistry

        mock_tool_result = MagicMock()
        mock_tool_result.data = mock_thread_detail_result

        mock_registry = MagicMock(spec=ToolRegistry)
        mock_registry.execute = AsyncMock(return_value=mock_tool_result)

        orchestrator = MailboxAgentOrchestrator(
            tool_registry=mock_registry,
            enable_llm_fallback=True,
        )

        # Mock LLM returning None (failure)
        with patch.object(
            orchestrator, "_call_llm_for_draft", new=AsyncMock(return_value=None)
        ):
            request = FollowupDraftRequest(
                user_id="test-user", thread_id="thread-123", mode="preview_only"
            )

            result = await orchestrator.draft_followup(request, mock_db_session)

            # Should return error
            assert result.status == "error"
            assert "LLM unavailable" in result.message
