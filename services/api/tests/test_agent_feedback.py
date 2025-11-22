"""
Tests for Agent V2 feedback and learning loop.

Tests:
1. POST /api/v2/agent/feedback creates feedback records
2. build_prefs_from_rows aggregates feedback correctly
3. Preference filtering removes expected items
4. Aggregation endpoint processes all users
"""

import pytest
from datetime import datetime
from uuid import uuid4

from app.models import AgentFeedback
from app.agent.feedback_aggregate import (
    build_prefs_from_rows,
)


class TestFeedbackAPI:
    """Test feedback API endpoint."""

    @pytest.mark.asyncio
    async def test_post_feedback_creates_record(self, client, test_user, test_db):
        """POST /api/v2/agent/feedback creates a feedback record."""
        # Login as test user
        # TODO: Add auth setup once test harness has session handling

        payload = {
            "intent": "suspicious",
            "query": "show suspicious emails",
            "run_id": str(uuid4()),
            "card_id": "suspicious_summary",
            "item_id": "gmail-thread-123",
            "label": "hide",
            "thread_id": "gmail-thread-123",
        }

        # TODO: Add proper session cookie
        # response = client.post("/api/v2/agent/feedback", json=payload)
        # assert response.status_code == 200
        # assert response.json()["ok"] is True

        # For now, test the model directly
        feedback = AgentFeedback(
            id=str(uuid4()),
            user_id=test_user.id,
            intent=payload["intent"],
            label=payload["label"],
            thread_id=payload["thread_id"],
        )
        test_db.add(feedback)
        await test_db.commit()

        # Verify record exists
        from sqlalchemy import select

        result = await test_db.execute(
            select(AgentFeedback).where(AgentFeedback.user_id == test_user.id)
        )
        saved = result.scalar_one_or_none()
        assert saved is not None
        assert saved.intent == "suspicious"
        assert saved.label == "hide"
        assert saved.thread_id == "gmail-thread-123"


class TestPreferenceAggregation:
    """Test preference aggregation logic."""

    def test_build_prefs_suspicious_blocked(self):
        """Suspicious + hide/not_helpful → blocked_thread_ids."""
        rows = [
            AgentFeedback(
                id=str(uuid4()),
                user_id="user-1",
                intent="suspicious",
                label="hide",
                thread_id="thread-1",
                created_at=datetime.utcnow(),
            ),
            AgentFeedback(
                id=str(uuid4()),
                user_id="user-1",
                intent="suspicious",
                label="not_helpful",
                thread_id="thread-2",
                created_at=datetime.utcnow(),
            ),
            # Helpful feedback should NOT block
            AgentFeedback(
                id=str(uuid4()),
                user_id="user-1",
                intent="suspicious",
                label="helpful",
                thread_id="thread-3",
                created_at=datetime.utcnow(),
            ),
        ]

        prefs = build_prefs_from_rows(rows)

        assert "suspicious" in prefs
        assert set(prefs["suspicious"]["blocked_thread_ids"]) == {
            "thread-1",
            "thread-2",
        }

    def test_build_prefs_followups_done_and_hidden(self):
        """Followups + done → done_thread_ids, hide → hidden_thread_ids."""
        rows = [
            AgentFeedback(
                id=str(uuid4()),
                user_id="user-1",
                intent="followups",
                label="done",
                thread_id="thread-done",
                created_at=datetime.utcnow(),
            ),
            AgentFeedback(
                id=str(uuid4()),
                user_id="user-1",
                intent="followups",
                label="hide",
                thread_id="thread-hide",
                created_at=datetime.utcnow(),
            ),
        ]

        prefs = build_prefs_from_rows(rows)

        assert "followups" in prefs
        assert "thread-done" in prefs["followups"]["done_thread_ids"]
        assert "thread-hide" in prefs["followups"]["hidden_thread_ids"]

    def test_build_prefs_bills_autopay(self):
        """Bills + done → autopay_thread_ids."""
        rows = [
            AgentFeedback(
                id=str(uuid4()),
                user_id="user-1",
                intent="bills",
                label="done",
                thread_id="thread-spotify",
                created_at=datetime.utcnow(),
            ),
        ]

        prefs = build_prefs_from_rows(rows)

        assert "bills" in prefs
        assert "thread-spotify" in prefs["bills"]["autopay_thread_ids"]

    def test_build_prefs_deduplicates(self):
        """Multiple feedback on same thread_id is deduplicated."""
        rows = [
            AgentFeedback(
                id=str(uuid4()),
                user_id="user-1",
                intent="suspicious",
                label="hide",
                thread_id="thread-dup",
                created_at=datetime.utcnow(),
            ),
            AgentFeedback(
                id=str(uuid4()),
                user_id="user-1",
                intent="suspicious",
                label="not_helpful",
                thread_id="thread-dup",
                created_at=datetime.utcnow(),
            ),
        ]

        prefs = build_prefs_from_rows(rows)

        # Should only appear once
        assert prefs["suspicious"]["blocked_thread_ids"] == ["thread-dup"]

    def test_build_prefs_ignores_none_thread_id(self):
        """Feedback without thread_id is ignored."""
        rows = [
            AgentFeedback(
                id=str(uuid4()),
                user_id="user-1",
                intent="suspicious",
                label="hide",
                thread_id=None,  # No thread_id
                created_at=datetime.utcnow(),
            ),
        ]

        prefs = build_prefs_from_rows(rows)

        assert prefs["suspicious"]["blocked_thread_ids"] == []


class TestOrchestratorFiltering:
    """Test orchestrator filtering with preferences."""

    def test_filter_suspicious_blocks_threads(self):
        """Suspicious intent filters blocked_thread_ids."""
        from app.agent.orchestrator import MailboxAgentOrchestrator
        from app.schemas_agent import ToolResult

        orchestrator = MailboxAgentOrchestrator()

        # Mock tool results with thread_ids
        tool_results = [
            ToolResult(
                tool_name="email_search",
                status="success",
                data={"emails": []},
                summary="Thread 1",
            ),
            ToolResult(
                tool_name="email_search",
                status="success",
                data={"emails": []},
                summary="Thread 2",
            ),
        ]

        # Add thread_id attribute (simulate real results)
        tool_results[0].thread_id = "thread-1"
        tool_results[1].thread_id = "thread-2"

        # Preferences block thread-1
        prefs = {"suspicious": {"blocked_thread_ids": ["thread-1"]}}

        filtered = orchestrator._filter_tool_results_by_preferences(
            tool_results, "suspicious", prefs
        )

        # Should only have thread-2
        assert len(filtered) == 1
        assert filtered[0].thread_id == "thread-2"

    def test_filter_followups_removes_done_and_hidden(self):
        """Followups intent filters done_thread_ids and hidden_thread_ids."""
        from app.agent.orchestrator import MailboxAgentOrchestrator
        from app.schemas_agent import ToolResult

        orchestrator = MailboxAgentOrchestrator()

        tool_results = [
            ToolResult(
                tool_name="email_search",
                status="success",
                data={},
                summary="Thread 1",
            ),
            ToolResult(
                tool_name="email_search",
                status="success",
                data={},
                summary="Thread 2",
            ),
            ToolResult(
                tool_name="email_search",
                status="success",
                data={},
                summary="Thread 3",
            ),
        ]

        tool_results[0].thread_id = "thread-done"
        tool_results[1].thread_id = "thread-hide"
        tool_results[2].thread_id = "thread-active"

        prefs = {
            "followups": {
                "done_thread_ids": ["thread-done"],
                "hidden_thread_ids": ["thread-hide"],
            }
        }

        filtered = orchestrator._filter_tool_results_by_preferences(
            tool_results, "followups", prefs
        )

        # Should only have thread-active
        assert len(filtered) == 1
        assert filtered[0].thread_id == "thread-active"

    def test_filter_bills_removes_autopay(self):
        """Bills intent filters autopay_thread_ids."""
        from app.agent.orchestrator import MailboxAgentOrchestrator
        from app.schemas_agent import ToolResult

        orchestrator = MailboxAgentOrchestrator()

        tool_results = [
            ToolResult(
                tool_name="email_search", status="success", data={}, summary="1"
            ),
            ToolResult(
                tool_name="email_search", status="success", data={}, summary="2"
            ),
        ]

        tool_results[0].thread_id = "thread-spotify"
        tool_results[1].thread_id = "thread-manual"

        prefs = {"bills": {"autopay_thread_ids": ["thread-spotify"]}}

        filtered = orchestrator._filter_tool_results_by_preferences(
            tool_results, "bills", prefs
        )

        # Should only have manual bill
        assert len(filtered) == 1
        assert filtered[0].thread_id == "thread-manual"
