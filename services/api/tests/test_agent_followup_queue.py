"""
Tests for Follow-up Queue endpoint and orchestrator method.

Tests verify:
- Endpoint returns merged threads + applications
- queue_meta.total matches number of items
- Applications without thread data are included
- Priority sorting works correctly
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request
from app.schemas_agent import (
    FollowupQueueRequest,
)


class TestFollowupQueueEndpoint:
    """Tests for POST /v2/agent/followup-queue endpoint."""

    @pytest.mark.asyncio
    async def test_followup_queue_merges_threads_and_applications(self):
        """Test that threads and applications are merged correctly."""
        from app.routers.agent import get_followup_queue
        from app.models import Application

        # Mock request with user_id
        mock_request = MagicMock(spec=Request)
        mock_request.state.session_user_id = "test-user"

        # Mock orchestrator response with threads
        mock_orchestrator = AsyncMock()
        mock_orchestrator.get_followup_queue.return_value = {
            "threads": [
                {
                    "thread_id": "thread-1",
                    "subject": "Interview Follow-up",
                    "snippet": "Thanks for the interview...",
                    "from": "recruiter@company.com",
                    "last_message_at": "2025-11-20T10:00:00Z",
                    "gmail_url": "https://mail.google.com/thread-1",
                    "priority": 50,
                },
                {
                    "thread_id": "thread-2",
                    "subject": "Application Status",
                    "snippet": "We received your application...",
                    "from": "hr@startup.com",
                    "last_message_at": "2025-11-19T15:00:00Z",
                    "gmail_url": "https://mail.google.com/thread-2",
                    "priority": 40,
                },
            ],
            "time_window_days": 30,
        }

        # Mock database query
        mock_db = MagicMock()
        mock_app_1 = MagicMock(spec=Application)
        mock_app_1.id = 101
        mock_app_1.thread_id = "thread-1"
        mock_app_1.company = "Big Tech Co"
        mock_app_1.role = "Software Engineer"
        mock_app_1.status = "interview"

        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.all.return_value = [mock_app_1]

        with patch(
            "app.routers.agent.get_orchestrator", return_value=mock_orchestrator
        ):
            payload = FollowupQueueRequest(user_id="test-user", time_window_days=30)
            response = await get_followup_queue(payload, mock_request, mock_db)

        assert response.status == "ok"
        assert response.queue_meta.total == 2
        assert response.queue_meta.time_window_days == 30
        assert len(response.items) == 2

        # First item should have boosted priority due to application
        first_item = response.items[0]
        assert first_item.thread_id == "thread-1"
        assert first_item.application_id == 101
        assert first_item.company == "Big Tech Co"
        assert first_item.role == "Software Engineer"
        assert first_item.priority >= 70  # Boosted
        assert "status:interview" in first_item.reason_tags

        # Second item has no application
        second_item = response.items[1]
        assert second_item.thread_id == "thread-2"
        assert second_item.application_id is None
        assert second_item.priority == 40

    @pytest.mark.asyncio
    async def test_followup_queue_includes_applications_without_threads(self):
        """Test that applications without matching thread data are included."""
        from app.routers.agent import get_followup_queue
        from app.models import Application

        mock_request = MagicMock(spec=Request)
        mock_request.state.session_user_id = "test-user"

        # Mock orchestrator with no threads
        mock_orchestrator = AsyncMock()
        mock_orchestrator.get_followup_queue.return_value = {
            "threads": [],
            "time_window_days": 30,
        }

        # Mock database with application that has thread_id but no thread data
        mock_db = MagicMock()
        mock_app = MagicMock(spec=Application)
        mock_app.id = 202
        mock_app.thread_id = "orphan-thread"
        mock_app.company = "Startup Inc"
        mock_app.role = "Frontend Dev"
        mock_app.status = "applied"

        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.all.return_value = [mock_app]

        with patch(
            "app.routers.agent.get_orchestrator", return_value=mock_orchestrator
        ):
            payload = FollowupQueueRequest(user_id="test-user")
            response = await get_followup_queue(payload, mock_request, mock_db)

        assert response.status == "ok"
        assert response.queue_meta.total == 1
        assert len(response.items) == 1

        item = response.items[0]
        assert item.thread_id == "orphan-thread"
        assert item.application_id == 202
        assert item.company == "Startup Inc"
        assert "no_thread_data" in item.reason_tags
        assert item.subject is None  # No thread data

    @pytest.mark.asyncio
    async def test_followup_queue_total_matches_items_count(self):
        """Test that queue_meta.total exactly matches the number of items."""
        from app.routers.agent import get_followup_queue
        from app.models import Application

        mock_request = MagicMock(spec=Request)
        mock_request.state.session_user_id = "test-user"

        # Mock with 3 threads and 2 applications
        mock_orchestrator = AsyncMock()
        mock_orchestrator.get_followup_queue.return_value = {
            "threads": [
                {"thread_id": f"thread-{i}", "priority": 50 - i * 5} for i in range(3)
            ],
            "time_window_days": 30,
        }

        mock_db = MagicMock()
        mock_apps = []
        for i in range(2):
            app = MagicMock(spec=Application)
            app.id = 300 + i
            app.thread_id = f"thread-{i}"
            app.company = f"Company {i}"
            app.role = "Engineer"
            app.status = "hr_screen"
            mock_apps.append(app)

        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.all.return_value = mock_apps

        with patch(
            "app.routers.agent.get_orchestrator", return_value=mock_orchestrator
        ):
            payload = FollowupQueueRequest(user_id="test-user", time_window_days=30)
            response = await get_followup_queue(payload, mock_request, mock_db)

        # Should have 3 threads total (2 with apps, 1 without)
        assert response.queue_meta.total == len(response.items)
        assert len(response.items) == 3

    @pytest.mark.asyncio
    async def test_followup_queue_sorted_by_priority(self):
        """Test that items are sorted by priority descending."""
        from app.routers.agent import get_followup_queue

        mock_request = MagicMock(spec=Request)
        mock_request.state.session_user_id = "test-user"

        mock_orchestrator = AsyncMock()
        mock_orchestrator.get_followup_queue.return_value = {
            "threads": [
                {"thread_id": "low", "priority": 20},
                {"thread_id": "high", "priority": 80},
                {"thread_id": "mid", "priority": 50},
            ],
            "time_window_days": 30,
        }

        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.all.return_value = []

        with patch(
            "app.routers.agent.get_orchestrator", return_value=mock_orchestrator
        ):
            payload = FollowupQueueRequest(user_id="test-user")
            response = await get_followup_queue(payload, mock_request, mock_db)

        # Should be sorted high to low
        priorities = [item.priority for item in response.items]
        assert priorities == sorted(priorities, reverse=True)
        assert response.items[0].thread_id == "high"
        assert response.items[2].thread_id == "low"

    @pytest.mark.asyncio
    async def test_followup_queue_applies_done_state(self):
        """Test that existing followup_queue_state rows mark items as done."""
        from app.routers.agent import get_followup_queue
        from app.models import Application, FollowupQueueState

        mock_request = MagicMock(spec=Request)
        mock_request.state.session_user_id = "test-user"

        mock_orchestrator = AsyncMock()
        mock_orchestrator.get_followup_queue.return_value = {
            "threads": [
                {"thread_id": "thread-1", "priority": 50},
                {"thread_id": "thread-2", "priority": 60},
                {"thread_id": "thread-3", "priority": 40},
            ],
            "time_window_days": 30,
        }

        # Mock database with one application and one done state
        mock_db = MagicMock()

        # Application for thread-1
        mock_app = MagicMock(spec=Application)
        mock_app.id = 100
        mock_app.thread_id = "thread-1"
        mock_app.company = "Test Co"
        mock_app.role = "Engineer"
        mock_app.status = "applied"

        # State marking thread-2 as done
        mock_state = MagicMock(spec=FollowupQueueState)
        mock_state.user_id = "test-user"
        mock_state.thread_id = "thread-2"
        mock_state.is_done = True

        # Setup query mocks
        def query_side_effect(model):
            mock_query = MagicMock()
            if model == Application:
                mock_query.filter.return_value.all.return_value = [mock_app]
            elif model == FollowupQueueState:
                mock_query.filter.return_value.all.return_value = [mock_state]
            return mock_query

        mock_db.query.side_effect = query_side_effect

        with patch(
            "app.routers.agent.get_orchestrator", return_value=mock_orchestrator
        ):
            payload = FollowupQueueRequest(user_id="test-user")
            response = await get_followup_queue(payload, mock_request, mock_db)

        assert response.status == "ok"
        assert response.queue_meta.total == 3
        assert response.queue_meta.done_count == 1
        assert response.queue_meta.remaining_count == 2

        # Find thread-2 and verify it's marked done
        thread_2_item = next(
            item for item in response.items if item.thread_id == "thread-2"
        )
        assert thread_2_item.is_done is True

        # Other threads should not be done
        thread_1_item = next(
            item for item in response.items if item.thread_id == "thread-1"
        )
        thread_3_item = next(
            item for item in response.items if item.thread_id == "thread-3"
        )
        assert thread_1_item.is_done is False
        assert thread_3_item.is_done is False


class TestOrchestratorGetFollowupQueue:
    """Tests for orchestrator.get_followup_queue method."""

    @pytest.mark.asyncio
    async def test_get_followup_queue_calls_agent_with_followups_intent(self):
        """Test that get_followup_queue calls agent run with correct intent."""
        from app.agent.orchestrator import MailboxAgentOrchestrator
        from app.schemas_agent import AgentRunResponse, AgentCard

        orchestrator = MailboxAgentOrchestrator()

        # Mock the run method
        mock_response = AgentRunResponse(
            run_id="test-run",
            status="completed",
            intent="followups",
            cards=[
                AgentCard(
                    card_type="thread_list",
                    data={
                        "threads": [
                            {
                                "thread_id": "test-thread",
                                "subject": "Test",
                                "priority": 60,
                            }
                        ]
                    },
                )
            ],
            metrics={},
        )

        orchestrator.run = AsyncMock(return_value=mock_response)

        result = await orchestrator.get_followup_queue(
            user_id="test-user",
            time_window_days=30,
        )

        # Verify run was called with followups intent
        orchestrator.run.assert_called_once()
        call_args = orchestrator.run.call_args
        req = call_args[0][0]
        assert req.intent == "followups"
        assert req.mode == "preview_only"
        assert req.time_window_days == 30

        # Verify result structure
        assert "threads" in result
        assert len(result["threads"]) == 1
        assert result["threads"][0]["thread_id"] == "test-thread"

    @pytest.mark.asyncio
    async def test_get_followup_queue_handles_empty_threads(self):
        """Test that get_followup_queue handles no threads gracefully."""
        from app.agent.orchestrator import MailboxAgentOrchestrator
        from app.schemas_agent import AgentRunResponse

        orchestrator = MailboxAgentOrchestrator()
        mock_response = AgentRunResponse(
            run_id="empty-run",
            status="completed",
            intent="followups",
            cards=[],
            metrics={},
        )

        orchestrator.run = AsyncMock(return_value=mock_response)

        result = await orchestrator.get_followup_queue(user_id="test-user")

        assert result["threads"] == []
        assert result["time_window_days"] == 30  # Default
