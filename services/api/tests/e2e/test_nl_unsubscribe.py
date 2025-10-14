"""
E2E Tests for NL Agent - Unsubscribe and Show Suspicious Commands

Tests natural language parsing for unsubscribe and suspicious email commands.
"""

import pytest


@pytest.mark.asyncio
async def test_nl_unsubscribe_candidates(monkeypatch, async_client):
    """Test that 'unsubscribe' command generates unsubscribe actions."""

    async def fake_candidates(days: int):
        return [
            {
                "id": "news_1",
                "has_unsubscribe": True,
                "sender_domain": "newsletter.example.com",
            }
        ]

    import app.logic.search as S

    monkeypatch.setattr(S, "find_unsubscribe_candidates", fake_candidates)

    r = await async_client.post(
        "/nl/run",
        json={"text": "unsubscribe from newsletters I haven't opened in 60 days"},
    )

    assert r.status_code == 200
    j = r.json()
    assert j["intent"] == "unsubscribe_stale"
    assert j["count"] == 1
    assert len(j["proposed_actions"]) == 1
    assert j["proposed_actions"][0]["action"] == "unsubscribe"
    assert j["proposed_actions"][0]["email_id"] == "news_1"


@pytest.mark.asyncio
async def test_nl_unsubscribe_custom_days(monkeypatch, async_client):
    """Test that custom days parameter is parsed for unsubscribe."""
    calls = []

    async def track_days(days: int):
        calls.append(days)
        return [{"id": "news_1", "has_unsubscribe": True}]

    import app.logic.search as S

    monkeypatch.setattr(S, "find_unsubscribe_candidates", track_days)

    r = await async_client.post(
        "/nl/run", json={"text": "unsubscribe from emails I haven't opened in 90 days"}
    )

    assert r.status_code == 200
    assert len(calls) == 1
    assert calls[0] == 90  # Should parse "90 days"


@pytest.mark.asyncio
async def test_nl_unsubscribe_default_days(monkeypatch, async_client):
    """Test that default of 60 days is used for unsubscribe when not specified."""
    calls = []

    async def track_days(days: int):
        calls.append(days)
        return []

    import app.logic.search as S

    monkeypatch.setattr(S, "find_unsubscribe_candidates", track_days)

    r = await async_client.post(
        "/nl/run", json={"text": "unsubscribe from old newsletters"}
    )

    assert r.status_code == 200
    assert calls[0] == 60  # Default


@pytest.mark.asyncio
async def test_nl_unsubscribe_multiple_candidates(monkeypatch, async_client):
    """Test generating unsubscribe actions for multiple senders."""

    async def multiple_senders(days: int):
        return [
            {"id": "news_1", "has_unsubscribe": True, "sender_domain": "news1.com"},
            {"id": "news_2", "has_unsubscribe": True, "sender_domain": "news2.com"},
            {"id": "news_3", "has_unsubscribe": True, "sender_domain": "news3.com"},
        ]

    import app.logic.search as S

    monkeypatch.setattr(S, "find_unsubscribe_candidates", multiple_senders)

    r = await async_client.post("/nl/run", json={"text": "unsubscribe from old stuff"})

    assert r.status_code == 200
    j = r.json()
    assert j["count"] == 3
    assert len(j["proposed_actions"]) == 3

    # Check all are unsubscribe actions
    for action in j["proposed_actions"]:
        assert action["action"] == "unsubscribe"
        assert action["policy_id"] == "unsubscribe-stale"
        assert action["confidence"] == 0.9


@pytest.mark.asyncio
async def test_nl_show_suspicious_emails(monkeypatch, async_client):
    """Test 'show suspicious' command returns high-risk emails."""

    async def fake_high_risk():
        return [
            {"id": "phish_1", "risk_score": 92, "category": "security"},
            {"id": "phish_2", "risk_score": 87, "category": "security"},
        ]

    import app.logic.search as S

    monkeypatch.setattr(S, "find_high_risk", fake_high_risk)

    r = await async_client.post("/nl/run", json={"text": "show me suspicious emails"})

    assert r.status_code == 200
    j = r.json()
    assert j["intent"] == "show_suspicious"
    assert j["count"] == 2
    assert len(j["emails"]) == 2
    assert j["emails"][0]["id"] == "phish_1"
    assert j["emails"][1]["id"] == "phish_2"


@pytest.mark.asyncio
async def test_nl_show_suspicious_variations(monkeypatch, async_client):
    """Test various phrasings for showing suspicious emails."""

    async def fake_high_risk():
        return [{"id": "phish_1", "risk_score": 90, "category": "security"}]

    import app.logic.search as S

    monkeypatch.setattr(S, "find_high_risk", fake_high_risk)

    variations = [
        "show suspicious emails",
        "show me fishy messages",
        "find potential phishing",
        "show risky emails",
        "find spam and malware",
    ]

    for text in variations:
        r = await async_client.post("/nl/run", json={"text": text})
        assert r.status_code == 200
        assert r.json()["intent"] == "show_suspicious"


@pytest.mark.asyncio
async def test_nl_fallback_unrecognized_command(async_client):
    """Test that unrecognized commands return fallback message."""
    r = await async_client.post("/nl/run", json={"text": "make me a sandwich"})

    assert r.status_code == 200
    j = r.json()
    assert j["intent"] == "fallback"
    assert "didn't understand" in j["message"].lower()


@pytest.mark.asyncio
async def test_nl_summarize_bills_placeholder(async_client):
    """Test that bills command returns coming soon message."""
    r = await async_client.post(
        "/nl/run", json={"text": "summarize my bills due next week"}
    )

    assert r.status_code == 200
    j = r.json()
    assert j["intent"] == "summarize_bills"
    assert "coming soon" in j["message"].lower()
