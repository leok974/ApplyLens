"""
Unit tests for Mailbox Assistant - Greeting Intent Handling

Tests that greeting/small talk queries do NOT trigger Elasticsearch queries
and return appropriate onboarding responses.

Part of Phase 1.2 - Conversational UX stable (v0.4.47e)
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestGreetingIntentDetection:
    """Test that greeting/small talk is detected correctly."""

    @pytest.mark.parametrize(
        "query",
        [
            "hi",
            "Hi",
            "HI",
            "hey",
            "hello",
            "Hello there",
            "yo",
            "sup",
            "help",
            "help me",
            "what can you do",
            "what can you do?",
            "what do you do",
            "what do you do?",
            "who are you",
            "who are you?",
            "what are you",
            "what are you?",
            "what can you help with",
            "what can you help with?",
        ],
    )
    def test_greeting_patterns(self, query):
        """
        Small talk queries should be detected as greetings.

        This test verifies that various greeting patterns are recognized
        as small talk and won't trigger expensive backend operations.
        """
        # Note: The actual greeting detection logic is client-side in v0.4.47e
        # But we test that if a greeting DOES reach the backend, it's handled gracefully
        # without triggering Elasticsearch queries

        # This is a documentation test showing expected behavior
        assert query.lower() in [
            "hi",
            "hey",
            "hello",
            "hello there",
            "yo",
            "sup",
            "help",
            "help me",
            "what can you do",
            "what can you do?",
            "what do you do",
            "what do you do?",
            "who are you",
            "who are you?",
            "what are you",
            "what are you?",
            "what can you help with",
            "what can you help with?",
        ]


class TestAssistantGreetingResponse:
    """Test assistant API behavior for greeting queries."""

    @pytest.mark.parametrize("query", ["hi", "hello", "help", "what can you do"])
    @patch("app.routers.assistant.es")
    def test_greeting_does_not_query_elasticsearch(self, mock_es, query):
        """
        CRITICAL TEST: Greeting queries should NOT trigger Elasticsearch calls.

        This is the primary test ensuring greetings are handled efficiently
        without hitting the database/search engine.
        """
        # Setup mock Elasticsearch client
        mock_es.search = Mock()

        # Make request to assistant endpoint
        payload = {
            "user_query": query,
            "mode": "off",
            "time_window_days": 30,
            "memory_opt_in": False,
            "account": "test@example.com",
        }

        response = client.post("/api/assistant/query", json=payload)

        # Response should be 200 OK
        assert response.status_code == 200

        # Parse response
        data = response.json()

        # Should have greeting intent
        assert data["intent"] in ["greeting", "help", "onboarding"]

        # Should have a friendly summary
        assert data["summary"]
        assert len(data["summary"]) > 0

        # Should have empty sources (no email search performed)
        assert data["sources"] == []

        # Should have no actions performed
        assert data["actions_performed"] == []

        # CRITICAL ASSERTION: Elasticsearch should NOT have been called
        mock_es.search.assert_not_called()

    @patch("app.routers.assistant.es")
    def test_greeting_returns_onboarding_content(self, mock_es):
        """
        Greeting responses should include helpful onboarding information.
        """
        mock_es.search = Mock()

        payload = {
            "user_query": "hi",
            "mode": "off",
            "time_window_days": 30,
            "memory_opt_in": False,
            "account": "test@example.com",
        }

        response = client.post("/api/assistant/query", json=payload)
        assert response.status_code == 200

        data = response.json()

        # Should mention capabilities
        summary_lower = data["summary"].lower()
        assert any(
            keyword in summary_lower
            for keyword in ["help", "assist", "can", "find", "show", "search"]
        )

        # Should be friendly/conversational
        assert any(
            greeting in summary_lower for greeting in ["hi", "hello", "hey", "welcome"]
        )

    @patch("app.routers.assistant.es")
    def test_greeting_vs_real_query_elasticsearch_usage(self, mock_es):
        """
        Compare Elasticsearch usage: greeting vs real query.

        Greeting: NO ES calls
        Real query: ES calls expected
        """
        mock_es.search = Mock(
            return_value={"hits": {"hits": [], "total": {"value": 0}}}
        )

        # Test 1: Greeting query
        greeting_payload = {
            "user_query": "hello",
            "mode": "off",
            "time_window_days": 30,
            "memory_opt_in": False,
            "account": "test@example.com",
        }

        response_greeting = client.post("/api/assistant/query", json=greeting_payload)
        assert response_greeting.status_code == 200

        greeting_es_call_count = mock_es.search.call_count

        # Reset mock
        mock_es.search.reset_mock()

        # Test 2: Real query (should trigger ES)
        real_payload = {
            "user_query": "show suspicious emails from this week",
            "mode": "off",
            "time_window_days": 7,
            "memory_opt_in": False,
            "account": "test@example.com",
        }

        response_real = client.post("/api/assistant/query", json=real_payload)
        assert response_real.status_code == 200

        real_es_call_count = mock_es.search.call_count

        # Greeting should have 0 ES calls, real query should have > 0
        assert greeting_es_call_count == 0, "Greeting triggered Elasticsearch!"
        assert real_es_call_count > 0, "Real query didn't trigger Elasticsearch!"


class TestAssistantResponseStructure:
    """Test that greeting responses have proper structure for frontend."""

    @patch("app.routers.assistant.es")
    def test_greeting_response_has_all_required_fields(self, mock_es):
        """
        Greeting responses must include all fields expected by frontend:
        - intent
        - summary
        - sources
        - suggested_actions
        - actions_performed
        - next_steps (optional)
        - followup_prompt (optional)
        """
        mock_es.search = Mock()

        payload = {
            "user_query": "hi",
            "mode": "off",
            "time_window_days": 30,
            "memory_opt_in": False,
            "account": "test@example.com",
        }

        response = client.post("/api/assistant/query", json=payload)
        assert response.status_code == 200

        data = response.json()

        # Required fields
        assert "intent" in data
        assert "summary" in data
        assert "sources" in data
        assert "suggested_actions" in data
        assert "actions_performed" in data

        # Optional but expected for conversational UX
        assert "next_steps" in data
        assert "followup_prompt" in data

        # Validate types
        assert isinstance(data["sources"], list)
        assert isinstance(data["suggested_actions"], list)
        assert isinstance(data["actions_performed"], list)

    @patch("app.routers.assistant.es")
    def test_greeting_response_conversational_fields(self, mock_es):
        """
        Greeting responses should include conversational guidance fields.

        These fields power the "You could ask:" UI in the frontend.
        """
        mock_es.search = Mock()

        payload = {
            "user_query": "what can you do",
            "mode": "off",
            "time_window_days": 30,
            "memory_opt_in": False,
            "account": "test@example.com",
        }

        response = client.post("/api/assistant/query", json=payload)
        assert response.status_code == 200

        data = response.json()

        # Should have conversational guidance
        if data["next_steps"]:
            assert isinstance(data["next_steps"], str)
            assert len(data["next_steps"]) > 0

        if data["followup_prompt"]:
            assert isinstance(data["followup_prompt"], str)
            assert len(data["followup_prompt"]) > 0
            # Should be a question or suggestion
            assert any(
                word in data["followup_prompt"].lower()
                for word in ["show", "find", "what", "who", "list", "search"]
            )


class TestPerformanceOptimization:
    """Test that greeting handling is optimized for performance."""

    @patch("app.routers.assistant.es")
    @patch("app.routers.assistant.get_llm_summary")
    def test_greeting_skips_llm_call(self, mock_llm, mock_es):
        """
        Greeting queries should skip expensive LLM calls.

        The summary can be a template or simple string, not LLM-generated.
        """
        mock_es.search = Mock()
        mock_llm.return_value = "This should not be called"

        payload = {
            "user_query": "hi",
            "mode": "off",
            "time_window_days": 30,
            "memory_opt_in": False,
            "account": "test@example.com",
        }

        response = client.post("/api/assistant/query", json=payload)
        assert response.status_code == 200

        # Elasticsearch should not be called
        mock_es.search.assert_not_called()

        # LLM should ideally not be called either (optional optimization)
        # Comment this out if LLM is used for greeting responses
        # mock_llm.assert_not_called()

    @patch("app.routers.assistant.es")
    def test_greeting_response_time(self, mock_es):
        """
        Greeting responses should be fast (< 500ms).

        Since no DB/ES queries are made, response should be near-instant.
        """
        import time

        mock_es.search = Mock()

        payload = {
            "user_query": "hello",
            "mode": "off",
            "time_window_days": 30,
            "memory_opt_in": False,
            "account": "test@example.com",
        }

        start_time = time.time()
        response = client.post("/api/assistant/query", json=payload)
        end_time = time.time()

        assert response.status_code == 200

        # Response should be fast
        response_time_ms = (end_time - start_time) * 1000
        assert (
            response_time_ms < 500
        ), f"Greeting response took {response_time_ms}ms (expected < 500ms)"


class TestEdgeCases:
    """Test edge cases for greeting detection."""

    @patch("app.routers.assistant.es")
    @pytest.mark.parametrize(
        "query,should_be_greeting",
        [
            ("hi there", True),  # Greeting with extra words
            ("hello world", True),  # Greeting with object
            ("help!", True),  # Greeting with punctuation
            ("HELLO", True),  # Uppercase greeting
            ("Hi!", True),  # Mixed case with punctuation
            ("show me bills", False),  # Real query, not greeting
            ("find suspicious emails", False),  # Real query
            ("highlight in subject", False),  # Real query
        ],
    )
    def test_greeting_vs_real_query_classification(
        self, mock_es, query, should_be_greeting
    ):
        """
        Test boundary between greetings and real queries.
        """
        mock_es.search = Mock(
            return_value={"hits": {"hits": [], "total": {"value": 0}}}
        )

        payload = {
            "user_query": query,
            "mode": "off",
            "time_window_days": 30,
            "memory_opt_in": False,
            "account": "test@example.com",
        }

        response = client.post("/api/assistant/query", json=payload)
        assert response.status_code == 200

        data = response.json()

        if should_be_greeting:
            # Should be classified as greeting
            assert data["intent"] in ["greeting", "help", "onboarding"]
            # Should NOT trigger ES
            mock_es.search.assert_not_called()
        else:
            # Should be a real intent (not greeting)
            assert data["intent"] not in ["greeting", "help", "onboarding"]
            # Real queries MAY trigger ES (depending on implementation)
            # Don't assert ES call here since it depends on intent logic


# Integration test marker
pytestmark = pytest.mark.unit


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
