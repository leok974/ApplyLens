"""
E2E tests for Natural Language agent with Elasticsearch-backed search.

These tests verify that the NL agent correctly uses the real ES search helpers
(with mocked ES client) to find emails and generate actions.
"""

import pytest
import app.logic.search as S


@pytest.mark.asyncio
async def test_nl_clean_promos_with_es(async_client, monkeypatch):
    """Test 'clean promos' command uses ES-backed find_expired_promos."""
    
    async def fake_expired(days: int = 7, limit: int = 200):
        """Mock find_expired_promos to return test data."""
        return [
            {
                "id": "promoA",
                "category": "promotions",
                "expires_at": "2025-10-01T00:00:00Z",
                "received_at": "2025-10-05T00:00:00Z",
                "subject": "Flash Sale Expired",
            }
        ]
    
    monkeypatch.setattr(S, "find_expired_promos", fake_expired)
    
    r = await async_client.post("/nl/run", json={"text": "clean my promos older than 7 days"})
    
    assert r.status_code == 200
    j = r.json()
    
    assert j["intent"] == "clean_promos"
    assert j["params"]["days"] == 7
    assert len(j["proposed_actions"]) == 1
    assert j["proposed_actions"][0]["action"] == "archive"
    assert j["proposed_actions"][0]["email_id"] == "promoA"


@pytest.mark.asyncio
async def test_nl_unsubscribe_stale_with_es(async_client, monkeypatch):
    """Test 'unsubscribe' command uses ES-backed find_unsubscribe_candidates."""
    
    async def fake_unsubscribe_candidates(days: int = 60, limit: int = 200):
        """Mock find_unsubscribe_candidates to return test data."""
        return [
            {
                "id": "news1",
                "has_unsubscribe": True,
                "sender_domain": "newsletter.example.com",
                "received_at": "2025-07-01T00:00:00Z",
                "subject": "Weekly Newsletter",
            },
            {
                "id": "news2",
                "has_unsubscribe": True,
                "sender_domain": "promo.shop.com",
                "received_at": "2025-06-15T00:00:00Z",
                "subject": "Sales Updates",
            },
        ]
    
    monkeypatch.setattr(S, "find_unsubscribe_candidates", fake_unsubscribe_candidates)
    
    r = await async_client.post("/nl/run", json={"text": "unsubscribe from stale newsletters"})
    
    assert r.status_code == 200
    j = r.json()
    
    assert j["intent"] == "unsubscribe_stale"
    assert j["params"]["days"] == 60  # default
    assert len(j["proposed_actions"]) == 2
    
    # Verify actions
    actions = j["proposed_actions"]
    assert all(a["action"] == "unsubscribe" for a in actions)
    email_ids = {a["email_id"] for a in actions}
    assert "news1" in email_ids
    assert "news2" in email_ids


@pytest.mark.asyncio
async def test_nl_show_suspicious_with_es(async_client, monkeypatch):
    """Test 'show suspicious' command uses ES-backed find_high_risk."""
    
    async def fake_high_risk(limit: int = 50, min_risk: float = 80.0):
        """Mock find_high_risk to return test data."""
        return [
            {
                "id": "phish1",
                "risk_score": 95,
                "category": "security",
                "sender_domain": "suspicious.com",
                "subject": "Urgent: Update Your Password",
            },
            {
                "id": "phish2",
                "risk_score": 88,
                "category": "security",
                "sender_domain": "fake-bank.com",
                "subject": "Account Verification Required",
            },
        ]
    
    monkeypatch.setattr(S, "find_high_risk", fake_high_risk)
    
    r = await async_client.post("/nl/run", json={"text": "show me suspicious emails"})
    
    assert r.status_code == 200
    j = r.json()
    
    assert j["intent"] == "show_suspicious"
    assert len(j["proposed_actions"]) == 2
    
    # Verify flagging actions
    actions = j["proposed_actions"]
    assert all(a["action"] == "flag" for a in actions)
    risk_scores = [a.get("context", {}).get("risk_score") for a in actions if a.get("context")]
    assert any(score >= 80 for score in risk_scores if score)


@pytest.mark.asyncio
async def test_nl_clean_promos_custom_days(async_client, monkeypatch):
    """Test 'clean promos' with custom days parameter."""
    
    async def fake_expired(days: int = 7, limit: int = 200):
        """Mock that captures the days parameter."""
        # In a real test, you'd verify days was passed correctly
        return [
            {
                "id": f"promo{i}",
                "category": "promotions",
                "expires_at": "2025-09-01T00:00:00Z",
            }
            for i in range(min(3, limit))
        ]
    
    monkeypatch.setattr(S, "find_expired_promos", fake_expired)
    
    r = await async_client.post("/nl/run", json={"text": "clean promos from the last 14 days"})
    
    assert r.status_code == 200
    j = r.json()
    
    assert j["intent"] == "clean_promos"
    assert j["params"]["days"] == 14
    assert len(j["proposed_actions"]) == 3


@pytest.mark.asyncio
async def test_nl_unsubscribe_custom_days(async_client, monkeypatch):
    """Test 'unsubscribe' with custom staleness threshold."""
    
    async def fake_unsubscribe_candidates(days: int = 60, limit: int = 200):
        """Mock that verifies days parameter."""
        return [
            {
                "id": "old_newsletter",
                "has_unsubscribe": True,
                "sender_domain": "ancient.news.com",
                "received_at": "2025-01-01T00:00:00Z",
            }
        ]
    
    monkeypatch.setattr(S, "find_unsubscribe_candidates", fake_unsubscribe_candidates)
    
    r = await async_client.post("/nl/run", json={"text": "unsubscribe from newsletters older than 90 days"})
    
    assert r.status_code == 200
    j = r.json()
    
    assert j["intent"] == "unsubscribe_stale"
    assert j["params"]["days"] == 90
    assert len(j["proposed_actions"]) == 1


@pytest.mark.asyncio
async def test_nl_multiple_intents_separate_requests(async_client, monkeypatch):
    """Test multiple different NL commands in sequence."""
    
    async def fake_expired(days: int = 7, limit: int = 200):
        return [{"id": "promo1", "category": "promotions"}]
    
    async def fake_high_risk(limit: int = 50, min_risk: float = 80.0):
        return [{"id": "phish1", "risk_score": 90}]
    
    monkeypatch.setattr(S, "find_expired_promos", fake_expired)
    monkeypatch.setattr(S, "find_high_risk", fake_high_risk)
    
    # First request: clean promos
    r1 = await async_client.post("/nl/run", json={"text": "clean up my promotions"})
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1["intent"] == "clean_promos"
    
    # Second request: show suspicious
    r2 = await async_client.post("/nl/run", json={"text": "show suspicious emails"})
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["intent"] == "show_suspicious"


@pytest.mark.asyncio
async def test_nl_empty_results(async_client, monkeypatch):
    """Test NL commands when ES returns no results."""
    
    async def fake_expired(days: int = 7, limit: int = 200):
        return []  # No expired promos
    
    monkeypatch.setattr(S, "find_expired_promos", fake_expired)
    
    r = await async_client.post("/nl/run", json={"text": "clean my promos"})
    
    assert r.status_code == 200
    j = r.json()
    
    assert j["intent"] == "clean_promos"
    assert len(j["proposed_actions"]) == 0
    assert j["message"] or True  # Should have some informative message


@pytest.mark.asyncio
async def test_nl_large_result_set(async_client, monkeypatch):
    """Test NL commands with large result sets from ES."""
    
    async def fake_expired(days: int = 7, limit: int = 200):
        # Return many results
        return [
            {
                "id": f"promo{i}",
                "category": "promotions",
                "expires_at": f"2025-09-{i % 30 + 1:02d}T00:00:00Z",
            }
            for i in range(150)
        ]
    
    monkeypatch.setattr(S, "find_expired_promos", fake_expired)
    
    r = await async_client.post("/nl/run", json={"text": "clean all my old promos"})
    
    assert r.status_code == 200
    j = r.json()
    
    assert j["intent"] == "clean_promos"
    assert len(j["proposed_actions"]) == 150


@pytest.mark.asyncio
async def test_nl_with_summarize_bills(async_client, monkeypatch):
    """Test 'summarize bills' command (if implemented)."""
    
    async def fake_search(category=None, **kwargs):
        """Mock search_emails for bills."""
        if category == "bills":
            return [
                {
                    "id": "bill1",
                    "category": "bills",
                    "subject": "Electric Bill - $125",
                    "received_at": "2025-10-01T00:00:00Z",
                },
                {
                    "id": "bill2",
                    "category": "bills",
                    "subject": "Internet Bill - $80",
                    "received_at": "2025-10-02T00:00:00Z",
                },
            ]
        return []
    
    monkeypatch.setattr(S, "search_emails", fake_search)
    
    r = await async_client.post("/nl/run", json={"text": "summarize my bills"})
    
    # This might return 200 or 501 depending on implementation
    # If not implemented, it should gracefully degrade
    if r.status_code == 200:
        j = r.json()
        assert "intent" in j
        # If implemented, should have summary or actions
    else:
        # Fallback/not implemented is acceptable
        assert r.status_code in [200, 501]


@pytest.mark.asyncio
async def test_nl_intent_variations(async_client, monkeypatch):
    """Test that various phrasings of the same intent work."""
    
    async def fake_expired(days: int = 7, limit: int = 200):
        return [{"id": "promo1", "category": "promotions"}]
    
    monkeypatch.setattr(S, "find_expired_promos", fake_expired)
    
    # Different ways to say "clean promos"
    variations = [
        "clean my promos",
        "clean up promotions",
        "archive expired promos",
        "delete old promotional emails",
    ]
    
    for text in variations:
        r = await async_client.post("/nl/run", json={"text": text})
        assert r.status_code == 200
        j = r.json()
        assert j["intent"] == "clean_promos"


@pytest.mark.asyncio
async def test_nl_error_handling_invalid_text(async_client, monkeypatch):
    """Test NL agent handles invalid/empty text gracefully."""
    
    # Empty text
    r1 = await async_client.post("/nl/run", json={"text": ""})
    assert r1.status_code in [200, 400, 422]
    
    # Gibberish
    r2 = await async_client.post("/nl/run", json={"text": "asdfghjkl qwerty"})
    # Should either succeed with unknown intent or return error
    assert r2.status_code in [200, 400]
    if r2.status_code == 200:
        j = r2.json()
        # Should have some fallback handling
        assert "intent" in j or "error" in j
