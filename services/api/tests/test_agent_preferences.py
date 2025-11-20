"""
Tests for Agent V2 Learning Loop - Preference Filtering

Ensures that user preferences (built from feedback) correctly filter
agent results so hidden/done/blocked items don't reappear.
"""

from app.agent.orchestrator import MailboxAgentOrchestrator


class FakeToolResult:
    """Mock tool result for testing filtering logic."""

    def __init__(self, thread_id: str, **kwargs):
        self.thread_id = thread_id
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return f"FakeToolResult(thread_id={self.thread_id})"


class TestPreferenceFiltering:
    """Test suite for _filter_tool_results_by_preferences."""

    def setup_method(self):
        """Create orchestrator instance for testing."""
        self.orchestrator = MailboxAgentOrchestrator()

    def test_followups_filter_respects_done_and_hidden_prefs(self):
        """Followups intent should filter out done and hidden threads."""
        prefs = {
            "followups": {
                "done_thread_ids": ["thread-followup-1"],
                "hidden_thread_ids": ["thread-followup-2"],
            }
        }
        tool_results = [
            FakeToolResult(thread_id="thread-followup-1"),
            FakeToolResult(thread_id="thread-followup-2"),
            FakeToolResult(thread_id="thread-followup-3"),
        ]

        filtered = self.orchestrator._filter_tool_results_by_preferences(
            intent="followups",
            tool_results=tool_results,
            prefs=prefs,
        )

        assert len(filtered) == 1
        assert [r.thread_id for r in filtered] == ["thread-followup-3"]

    def test_suspicious_filter_respects_blocked_prefs(self):
        """Suspicious intent should filter out blocked threads."""
        prefs = {
            "suspicious": {
                "blocked_thread_ids": ["thread-sus-1", "thread-sus-2"],
            }
        }
        tool_results = [
            FakeToolResult(thread_id="thread-sus-1"),
            FakeToolResult(thread_id="thread-sus-2"),
            FakeToolResult(thread_id="thread-sus-3"),
            FakeToolResult(thread_id="thread-sus-4"),
        ]

        filtered = self.orchestrator._filter_tool_results_by_preferences(
            intent="suspicious",
            tool_results=tool_results,
            prefs=prefs,
        )

        assert len(filtered) == 2
        assert [r.thread_id for r in filtered] == ["thread-sus-3", "thread-sus-4"]

    def test_bills_filter_respects_autopay_prefs(self):
        """Bills intent should filter out autopay threads."""
        prefs = {
            "bills": {
                "autopay_thread_ids": ["bill-thread-1"],
            }
        }
        tool_results = [
            FakeToolResult(thread_id="bill-thread-1"),
            FakeToolResult(thread_id="bill-thread-2"),
            FakeToolResult(thread_id="bill-thread-3"),
        ]

        filtered = self.orchestrator._filter_tool_results_by_preferences(
            intent="bills",
            tool_results=tool_results,
            prefs=prefs,
        )

        assert len(filtered) == 2
        assert [r.thread_id for r in filtered] == ["bill-thread-2", "bill-thread-3"]

    def test_empty_prefs_returns_all_results(self):
        """No preferences means no filtering."""
        tool_results = [
            FakeToolResult(thread_id="thread-1"),
            FakeToolResult(thread_id="thread-2"),
        ]

        filtered = self.orchestrator._filter_tool_results_by_preferences(
            intent="followups",
            tool_results=tool_results,
            prefs={},
        )

        assert len(filtered) == 2
        assert filtered == tool_results

    def test_missing_thread_id_not_filtered(self):
        """Results without thread_id attribute should pass through."""
        prefs = {
            "suspicious": {
                "blocked_thread_ids": ["thread-1"],
            }
        }

        # Mix of results with and without thread_id
        class NoThreadResult:
            def __init__(self, name):
                self.name = name

        tool_results = [
            FakeToolResult(thread_id="thread-1"),
            NoThreadResult(name="no-thread-result"),
            FakeToolResult(thread_id="thread-2"),
        ]

        filtered = self.orchestrator._filter_tool_results_by_preferences(
            intent="suspicious",
            tool_results=tool_results,
            prefs=prefs,
        )

        # thread-1 blocked, no-thread-result passes, thread-2 passes
        assert len(filtered) == 2
        assert filtered[0].name == "no-thread-result"
        assert filtered[1].thread_id == "thread-2"

    def test_followups_empty_lists_no_filtering(self):
        """Empty preference lists should not filter anything."""
        prefs = {
            "followups": {
                "done_thread_ids": [],
                "hidden_thread_ids": [],
            }
        }
        tool_results = [
            FakeToolResult(thread_id="thread-1"),
            FakeToolResult(thread_id="thread-2"),
        ]

        filtered = self.orchestrator._filter_tool_results_by_preferences(
            intent="followups",
            tool_results=tool_results,
            prefs=prefs,
        )

        assert len(filtered) == 2
        assert filtered == tool_results

    def test_unknown_intent_no_filtering(self):
        """Unknown intent should pass through all results."""
        prefs = {
            "suspicious": {
                "blocked_thread_ids": ["thread-1"],
            }
        }
        tool_results = [
            FakeToolResult(thread_id="thread-1"),
            FakeToolResult(thread_id="thread-2"),
        ]

        filtered = self.orchestrator._filter_tool_results_by_preferences(
            intent="unknown_intent",
            tool_results=tool_results,
            prefs=prefs,
        )

        # Unknown intent doesn't have filtering logic, returns all
        assert len(filtered) == 2
        assert filtered == tool_results

    def test_followups_filter_all_results(self):
        """All results can be filtered if all are in preferences."""
        prefs = {
            "followups": {
                "done_thread_ids": ["thread-1", "thread-2"],
                "hidden_thread_ids": [],
            }
        }
        tool_results = [
            FakeToolResult(thread_id="thread-1"),
            FakeToolResult(thread_id="thread-2"),
        ]

        filtered = self.orchestrator._filter_tool_results_by_preferences(
            intent="followups",
            tool_results=tool_results,
            prefs=prefs,
        )

        assert len(filtered) == 0

    def test_case_sensitive_thread_ids(self):
        """Thread IDs should be case-sensitive."""
        prefs = {
            "suspicious": {
                "blocked_thread_ids": ["Thread-1"],  # Capital T
            }
        }
        tool_results = [
            FakeToolResult(thread_id="thread-1"),  # lowercase t
            FakeToolResult(thread_id="Thread-1"),  # matches
        ]

        filtered = self.orchestrator._filter_tool_results_by_preferences(
            intent="suspicious",
            tool_results=tool_results,
            prefs=prefs,
        )

        # Only exact match filtered
        assert len(filtered) == 1
        assert filtered[0].thread_id == "thread-1"
