"""
Tests for Agent V2 Thread Viewer → Tracker observability metrics.

Validates that:
1. applylens_agent_runs_total increments on successful agent runs
2. applylens_agent_threadlist_returned_total increments when thread_list cards are returned
3. POST /metrics/thread-to-tracker-click increments the click counter
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.agent.metrics import (
    applylens_agent_runs_total,
    applylens_agent_threadlist_returned_total,
    applylens_agent_thread_to_tracker_click_total,
    record_agent_run,
    record_threadlist_returned,
    record_thread_to_tracker_click,
)
from app.schemas_agent import AgentRunRequest, AgentContext, AgentCard


client = TestClient(app)


class TestAgentRunMetrics:
    """Test agent run counter metrics."""

    def test_record_agent_run_increments_counter(self):
        """Test that record_agent_run increments applylens_agent_runs_total for successful runs."""
        # Get initial counter value
        initial_value = applylens_agent_runs_total.labels(
            intent="followups"
        )._value.get()

        # Record a successful agent run
        record_agent_run(
            intent="followups",
            mode="preview_only",
            status="success",
            duration_ms=1500,
        )

        # Verify counter incremented
        new_value = applylens_agent_runs_total.labels(intent="followups")._value.get()
        assert new_value == initial_value + 1

    def test_record_agent_run_does_not_increment_on_error(self):
        """Test that error status runs don't increment applylens_agent_runs_total."""
        # Get initial counter value for bills intent
        initial_value = applylens_agent_runs_total.labels(intent="bills")._value.get()

        # Record an error agent run
        record_agent_run(
            intent="bills",
            mode="normal",
            status="error",
            duration_ms=500,
        )

        # Verify counter did NOT increment
        new_value = applylens_agent_runs_total.labels(intent="bills")._value.get()
        assert new_value == initial_value  # No change


class TestThreadListMetrics:
    """Test thread_list card return metrics."""

    def test_record_threadlist_returned_increments_with_threads(self):
        """Test that record_threadlist_returned increments when thread_count > 0."""
        # Get initial counter value
        initial_value = applylens_agent_threadlist_returned_total.labels(
            intent="followups"
        )._value.get()

        # Record thread_list return with 5 threads
        record_threadlist_returned(intent="followups", thread_count=5)

        # Verify counter incremented
        new_value = applylens_agent_threadlist_returned_total.labels(
            intent="followups"
        )._value.get()
        assert new_value == initial_value + 1

    def test_record_threadlist_returned_does_not_increment_with_zero_threads(self):
        """Test that record_threadlist_returned does NOT increment when thread_count == 0."""
        # Get initial counter value for suspicious intent
        initial_value = applylens_agent_threadlist_returned_total.labels(
            intent="suspicious"
        )._value.get()

        # Record thread_list return with 0 threads
        record_threadlist_returned(intent="suspicious", thread_count=0)

        # Verify counter did NOT increment
        new_value = applylens_agent_threadlist_returned_total.labels(
            intent="suspicious"
        )._value.get()
        assert new_value == initial_value  # No change


class TestThreadToTrackerClickMetrics:
    """Test thread-to-tracker click tracking."""

    def test_record_thread_to_tracker_click_increments(self):
        """Test that record_thread_to_tracker_click increments the counter."""
        # Get initial counter value
        initial_value = applylens_agent_thread_to_tracker_click_total._value.get()

        # Record a click
        record_thread_to_tracker_click()

        # Verify counter incremented
        new_value = applylens_agent_thread_to_tracker_click_total._value.get()
        assert new_value == initial_value + 1


@pytest.mark.asyncio
class TestThreadToTrackerClickEndpoint:
    """Test POST /metrics/thread-to-tracker-click endpoint."""

    async def test_endpoint_returns_200_and_increments_counter(self):
        """Test that the endpoint returns 200 and increments the counter."""
        # Get initial counter value
        initial_value = applylens_agent_thread_to_tracker_click_total._value.get()

        # Make POST request
        response = client.post(
            "/metrics/thread-to-tracker-click",
            json={
                "application_id": 123,
                "intent": "followups",
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["application_id"] == 123

        # Verify counter incremented
        new_value = applylens_agent_thread_to_tracker_click_total._value.get()
        assert new_value == initial_value + 1

    async def test_endpoint_accepts_null_intent(self):
        """Test that the endpoint accepts intent=null."""
        # Get initial counter value
        initial_value = applylens_agent_thread_to_tracker_click_total._value.get()

        # Make POST request with null intent
        response = client.post(
            "/metrics/thread-to-tracker-click",
            json={
                "application_id": 456,
                "intent": None,
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["application_id"] == 456

        # Verify counter still incremented
        new_value = applylens_agent_thread_to_tracker_click_total._value.get()
        assert new_value == initial_value + 1

    async def test_endpoint_rejects_invalid_payload(self):
        """Test that the endpoint rejects invalid payloads."""
        # Missing application_id
        response = client.post(
            "/metrics/thread-to-tracker-click",
            json={
                "intent": "followups",
            },
        )

        # Verify 422 Unprocessable Entity
        assert response.status_code == 422


@pytest.mark.asyncio
class TestIntegrationAgentToMetrics:
    """Integration test for agent run → metrics tracking."""

    @patch("app.agent.orchestrator.MailboxAgentOrchestrator._execute_tools")
    @patch("app.agent.orchestrator.complete_agent_answer")
    async def test_agent_run_with_threadlist_increments_both_counters(
        self, mock_complete_answer, mock_execute_tools
    ):
        """Test that an agent run with thread_list card increments both counters."""
        from app.agent.orchestrator import MailboxAgentOrchestrator
        from app.schemas_agent import ToolResult

        # Get initial counter values
        initial_runs = applylens_agent_runs_total.labels(
            intent="followups"
        )._value.get()
        initial_threadlists = applylens_agent_threadlist_returned_total.labels(
            intent="followups"
        )._value.get()

        # Mock tool execution to return empty results
        mock_execute_tools.return_value = [
            ToolResult(
                tool_name="email_search",
                status="success",
                summary="Found 3 threads",
                data={
                    "emails": [
                        {"id": "1", "thread_id": "t1", "subject": "Test 1"},
                        {"id": "2", "thread_id": "t2", "subject": "Test 2"},
                        {"id": "3", "thread_id": "t3", "subject": "Test 3"},
                    ],
                    "total": 3,
                    "time_window_days": 30,
                },
                duration_ms=100,
            ),
        ]

        # Mock LLM answer to return thread_list card
        mock_answer = "You have 3 conversations waiting for your reply."
        mock_cards = [
            AgentCard(
                kind="followups_summary",
                title="Conversations Waiting on Your Reply",
                body="You have 3 follow-ups awaiting your reply.",
                email_ids=[],
                threads=[],
                meta={"count": 3, "time_window_days": 30},
            ),
            AgentCard(
                kind="thread_list",
                intent="followups",
                title="Conversations Waiting on Your Reply",
                body="",
                email_ids=[],
                threads=[
                    {
                        "threadId": "t1",
                        "subject": "Test 1",
                        "from": "test1@example.com",
                        "lastMessageAt": "2025-01-01T00:00:00Z",
                    },
                    {
                        "threadId": "t2",
                        "subject": "Test 2",
                        "from": "test2@example.com",
                        "lastMessageAt": "2025-01-02T00:00:00Z",
                    },
                    {
                        "threadId": "t3",
                        "subject": "Test 3",
                        "from": "test3@example.com",
                        "lastMessageAt": "2025-01-03T00:00:00Z",
                    },
                ],
                meta={"count": 3, "time_window_days": 30},
            ),
        ]
        mock_complete_answer.return_value = (mock_answer, mock_cards)

        # Create request
        request = AgentRunRequest(
            query="show me follow-ups",
            mode="preview_only",
            context=AgentContext(time_window_days=30),
            user_id="test@example.com",
        )

        # Run orchestrator
        orch = MailboxAgentOrchestrator()
        response = await orch.run(request)

        # Verify response has thread_list card
        assert response.status == "done"
        thread_list_cards = [c for c in response.cards if c.kind == "thread_list"]
        assert len(thread_list_cards) == 1
        assert len(thread_list_cards[0].threads) == 3

        # Verify both counters incremented
        new_runs = applylens_agent_runs_total.labels(intent="followups")._value.get()
        new_threadlists = applylens_agent_threadlist_returned_total.labels(
            intent="followups"
        )._value.get()

        assert new_runs == initial_runs + 1
        assert new_threadlists == initial_threadlists + 1

    @patch("app.agent.orchestrator.MailboxAgentOrchestrator._execute_tools")
    @patch("app.agent.orchestrator.complete_agent_answer")
    async def test_agent_run_without_threadlist_only_increments_runs(
        self, mock_complete_answer, mock_execute_tools
    ):
        """Test that an agent run without thread_list card only increments runs counter."""
        from app.agent.orchestrator import MailboxAgentOrchestrator
        from app.schemas_agent import ToolResult

        # Get initial counter values
        initial_runs = applylens_agent_runs_total.labels(
            intent="suspicious"
        )._value.get()
        initial_threadlists = applylens_agent_threadlist_returned_total.labels(
            intent="suspicious"
        )._value.get()

        # Mock tool execution to return zero results
        mock_execute_tools.return_value = [
            ToolResult(
                tool_name="security_scan",
                status="success",
                summary="No suspicious emails found",
                data={
                    "emails_scanned": 50,
                    "matches": [],
                    "high_risk_count": 0,
                },
                duration_ms=100,
            ),
        ]

        # Mock LLM answer to return only summary card (no thread_list)
        mock_answer = "No suspicious emails found in your inbox."
        mock_cards = [
            AgentCard(
                kind="suspicious_summary",
                title="No Suspicious Emails Found",
                body="I scanned 50 emails and found no suspicious activity.",
                email_ids=[],
                threads=[],
                meta={"count": 0, "time_window_days": 30},
            ),
        ]
        mock_complete_answer.return_value = (mock_answer, mock_cards)

        # Create request
        request = AgentRunRequest(
            query="check for suspicious emails",
            mode="preview_only",
            context=AgentContext(time_window_days=30),
            user_id="test@example.com",
        )

        # Run orchestrator
        orch = MailboxAgentOrchestrator()
        response = await orch.run(request)

        # Verify response has NO thread_list card
        assert response.status == "done"
        thread_list_cards = [c for c in response.cards if c.kind == "thread_list"]
        assert len(thread_list_cards) == 0

        # Verify only runs counter incremented
        new_runs = applylens_agent_runs_total.labels(intent="suspicious")._value.get()
        new_threadlists = applylens_agent_threadlist_returned_total.labels(
            intent="suspicious"
        )._value.get()

        assert new_runs == initial_runs + 1
        assert new_threadlists == initial_threadlists  # No change
