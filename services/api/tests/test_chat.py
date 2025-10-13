"""
Tests for Phase 5 - Chat Assistant

Tests intent detection, RAG search, and chat endpoint functionality.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.intent import detect_intent, explain_intent
from app.main import app

client = TestClient(app)


class TestIntentDetection:
    """Test intent detection from user queries."""

    def test_detect_summarize(self):
        assert detect_intent("Summarize my recent emails") == "summarize"
        assert detect_intent("Tell me about emails from last week") == "summarize"
        assert detect_intent("What emails came in today?") == "summarize"

    def test_detect_find(self):
        assert detect_intent("Find emails from recruiters") == "find"
        assert detect_intent("Show me emails about interviews") == "find"
        assert detect_intent("Search for bills") == "find"

    def test_detect_clean(self):
        assert detect_intent("Clean up old promos") == "clean"
        assert detect_intent("Archive promotional emails") == "clean"
        assert detect_intent("Declutter my inbox") == "clean"

    def test_detect_unsubscribe(self):
        assert detect_intent("Unsubscribe from newsletters") == "unsubscribe"
        assert detect_intent("Opt out of marketing emails") == "unsubscribe"

    def test_detect_flag(self):
        assert detect_intent("Show suspicious emails") == "flag"
        assert detect_intent("Find phishing attempts") == "flag"
        assert detect_intent("Flag high-risk emails from new domains") == "flag"

    def test_detect_follow_up(self):
        assert detect_intent("Which emails need follow-up?") == "follow-up"
        assert detect_intent("Emails that need reply") == "follow-up"
        assert detect_intent("Recruiters who haven't responded") == "follow-up"

    def test_detect_calendar(self):
        assert detect_intent("Create calendar reminders for bills") == "calendar"
        assert detect_intent("What's due before Friday?") == "calendar"
        assert detect_intent("Add events to my calendar") == "calendar"

    def test_detect_task(self):
        assert detect_intent("Create tasks from emails") == "task"
        assert detect_intent("Make a todo list from my inbox") == "task"

    def test_fallback_to_summarize(self):
        """Unknown intents should default to summarize."""
        assert detect_intent("Random query here") == "summarize"
        assert detect_intent("What's going on?") == "summarize"

    def test_intent_explanations(self):
        """All intents should have explanations."""
        for intent in [
            "summarize",
            "find",
            "clean",
            "unsubscribe",
            "flag",
            "follow-up",
            "calendar",
            "task",
        ]:
            explanation = explain_intent(intent)
            assert explanation
            assert len(explanation) > 0


class TestChatEndpoint:
    """Test the /chat endpoint."""

    def test_chat_health(self):
        """Health check should work."""
        response = client.get("/api/chat/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "chat"

    def test_list_intents(self):
        """Should list all available intents."""
        response = client.get("/api/chat/intents")
        assert response.status_code == 200
        data = response.json()

        # Should have all 8 intents
        assert "summarize" in data
        assert "find" in data
        assert "clean" in data
        assert "unsubscribe" in data
        assert "flag" in data
        assert "follow-up" in data
        assert "calendar" in data
        assert "task" in data

        # Each intent should have patterns and description
        for intent, info in data.items():
            assert "patterns" in info
            assert "description" in info
            assert isinstance(info["patterns"], list)
            assert len(info["patterns"]) > 0

    def test_chat_empty_message(self):
        """Should reject empty messages."""
        response = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": ""}]},
        )
        assert response.status_code == 400
        assert "Empty message" in response.json()["detail"]

    def test_chat_no_messages(self):
        """Should reject requests with no messages."""
        response = client.post("/api/chat", json={"messages": []})
        assert response.status_code == 400
        assert "No messages" in response.json()["detail"]

    def test_chat_basic_query(self):
        """Should handle basic chat query."""
        response = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Summarize recent emails"}]},
        )
        assert response.status_code == 200
        data = response.json()

        # Should have expected structure
        assert "intent" in data
        assert "intent_explanation" in data
        assert "answer" in data
        assert "actions" in data
        assert "citations" in data
        assert "search_stats" in data

        # Intent should be summarize
        assert data["intent"] == "summarize"

        # Should have search stats
        stats = data["search_stats"]
        assert "total_results" in stats
        assert "returned_results" in stats
        assert "query" in stats

    def test_chat_with_filters(self):
        """Should accept structured filters."""
        response = client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "Show me promotional emails"}],
                "filters": {"category": "promotions"},
                "max_results": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Filters should be in search stats
        assert data["search_stats"]["filters"]["category"] == "promotions"

    def test_chat_clean_intent(self):
        """Should detect clean intent and propose actions."""
        response = client.post(
            "/api/chat",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": "Clean up promos older than a week",
                    }
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["intent"] == "clean"
        # May have actions (depends on test data)
        assert isinstance(data["actions"], list)

    def test_chat_calendar_intent(self):
        """Should detect calendar intent."""
        response = client.post(
            "/api/chat",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": "What bills are due before Friday? Create calendar reminders.",
                    }
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["intent"] == "calendar"

    def test_chat_flag_intent(self):
        """Should detect flag intent."""
        response = client.post(
            "/api/chat",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": "Show suspicious emails from new domains this week",
                    }
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["intent"] == "flag"

    def test_chat_conversation_history(self):
        """Should accept multi-turn conversations."""
        response = client.post(
            "/api/chat",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": "Summarize job application emails",
                    },
                    {"role": "assistant", "content": "Here are your job emails..."},
                    {
                        "role": "user",
                        "content": "Now show me interviews scheduled",
                    },
                ]
            },
        )
        assert response.status_code == 200
        # Should process last message
        data = response.json()
        assert data["intent"] in ["find", "summarize"]

    def test_chat_action_structure(self):
        """Actions should have proper structure."""
        response = client.post(
            "/api/chat",
            json={
                "messages": [
                    {"role": "user", "content": "Create tasks from recent emails"}
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()

        # If actions exist, they should have proper structure
        for action in data["actions"]:
            assert "action" in action
            assert "email_id" in action
            assert "params" in action
            assert isinstance(action["params"], dict)

    def test_chat_citation_structure(self):
        """Citations should have proper structure."""
        response = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Find recent emails"}]},
        )
        assert response.status_code == 200
        data = response.json()

        # If citations exist, they should have proper structure
        for citation in data["citations"]:
            assert "id" in citation
            assert "subject" in citation
            # Optional fields
            assert "sender" in citation or citation.get("sender") is None
            assert "received_at" in citation or citation.get("received_at") is None


class TestMailTools:
    """Test mail tool functions directly."""

    def test_clean_promos_with_exceptions(self):
        """Clean tool should respect exceptions in user text."""
        from datetime import datetime, timedelta

        from app.core.mail_tools import clean_promos

        # Mock RAG result with old promos
        week_ago = (datetime.utcnow() - timedelta(days=8)).isoformat()
        rag = {
            "docs": [
                {
                    "id": "1",
                    "subject": "Sale at Best Buy!",
                    "sender": "deals@bestbuy.com",
                    "category": "promotions",
                    "received_at": week_ago,
                },
                {
                    "id": "2",
                    "subject": "Daily deals",
                    "sender": "promo@example.com",
                    "category": "promotions",
                    "received_at": week_ago,
                },
            ]
        }

        user_text = "Clean up old promos unless they're from Best Buy"
        answer, actions = clean_promos(rag, user_text)

        # Should only archive the non-Best Buy email
        assert len(actions) == 1
        assert actions[0]["email_id"] == "2"
        assert "Best Buy" in answer or "best buy" in answer

    def test_calendar_events_date_extraction(self):
        """Calendar tool should extract due dates from user text."""
        from app.core.mail_tools import create_calendar_events

        rag = {
            "docs": [
                {
                    "id": "1",
                    "subject": "Bill payment due",
                    "sender": "billing@example.com",
                }
            ]
        }

        user_text = "Bills due before Friday"
        answer, actions = create_calendar_events(rag, user_text)

        # Should create calendar action
        assert len(actions) == 1
        assert actions[0]["action"] == "create_calendar_event"
        assert "when" in actions[0]["params"]


def test_intent_explain_tokens():
    """Test that intent explanation returns matched regex tokens."""
    from app.core.intent import explain_intent_tokens

    text = "Clean up promos before Friday unless they're from Best Buy"
    tokens = explain_intent_tokens(text)

    # Should match clean, before, unless phrases
    assert len(tokens) > 0
    assert any("clean" in t.lower() for t in tokens)
    assert any("unless" in t.lower() for t in tokens)
    assert any("before" in t.lower() for t in tokens)


def test_extract_unless_brands():
    """Test extraction of brand names from 'unless' clauses."""
    from app.core.intent import extract_unless_brands

    # Single brand
    text1 = "Clean promos unless they're from Best Buy"
    brands1 = extract_unless_brands(text1)
    assert len(brands1) == 1
    assert "best buy" in brands1[0].lower()

    # Multiple brands
    text2 = "Archive old emails unless from Best Buy and Costco"
    brands2 = extract_unless_brands(text2)
    assert len(brands2) == 2
    assert any("best buy" in b.lower() for b in brands2)
    assert any("costco" in b.lower() for b in brands2)

    # No unless clause
    text3 = "Just clean up old promos"
    brands3 = extract_unless_brands(text3)
    assert len(brands3) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
