"""
E2E Tests for NL Agent - Clean Promos Command

Tests natural language parsing and execution of "clean promos" command.
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_nl_clean_promos_generates_actions(monkeypatch):
    """Test that 'clean promos' command generates archive actions."""
    # Mock find_expired_promos to return test data
    async def fake_expired(days: int):
        return [{
            "id": "promoA",
            "category": "promotions",
            "expires_at": "2025-10-01T00:00:00Z"
        }]
    
    import app.logic.search as S
    monkeypatch.setattr(S, "find_expired_promos", fake_expired)
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/nl/run", json={"text": "clean my promos older than 7 days"})
        
        assert r.status_code == 200
        j = r.json()
        assert j["intent"] == "clean_promos"
        assert j["count"] >= 1
        assert len(j["proposed_actions"]) >= 1
        assert j["proposed_actions"][0]["action"] == "archive"
        assert j["proposed_actions"][0]["email_id"] == "promoA"


@pytest.mark.asyncio
async def test_nl_clean_promos_custom_days(monkeypatch):
    """Test that custom days parameter is parsed correctly."""
    calls = []
    
    async def track_days(days: int):
        calls.append(days)
        return [{
            "id": "promo1",
            "category": "promotions",
            "expires_at": "2025-09-15T00:00:00Z"
        }]
    
    import app.logic.search as S
    monkeypatch.setattr(S, "find_expired_promos", track_days)
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/nl/run", json={"text": "clean promos older than 14 days"})
        
        assert r.status_code == 200
        assert len(calls) == 1
        assert calls[0] == 14  # Should parse "14 days"


@pytest.mark.asyncio
async def test_nl_clean_promos_default_days(monkeypatch):
    """Test that default of 7 days is used when not specified."""
    calls = []
    
    async def track_days(days: int):
        calls.append(days)
        return []
    
    import app.logic.search as S
    monkeypatch.setattr(S, "find_expired_promos", track_days)
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/nl/run", json={"text": "clean my promos"})
        
        assert r.status_code == 200
        assert calls[0] == 7  # Default


@pytest.mark.asyncio
async def test_nl_clean_promos_no_matches(monkeypatch):
    """Test behavior when no expired promos are found."""
    async def no_results(days: int):
        return []
    
    import app.logic.search as S
    monkeypatch.setattr(S, "find_expired_promos", no_results)
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/nl/run", json={"text": "clean my promos"})
        
        assert r.status_code == 200
        j = r.json()
        assert j["intent"] == "clean_promos"
        assert j["count"] == 0
        assert len(j["proposed_actions"]) == 0


@pytest.mark.asyncio
async def test_nl_clean_promos_multiple_emails(monkeypatch):
    """Test generating actions for multiple emails."""
    async def multiple_promos(days: int):
        return [
            {"id": "promo1", "category": "promotions", "expires_at": "2025-10-01T00:00:00Z"},
            {"id": "promo2", "category": "promotions", "expires_at": "2025-10-02T00:00:00Z"},
            {"id": "promo3", "category": "promotions", "expires_at": "2025-10-03T00:00:00Z"}
        ]
    
    import app.logic.search as S
    monkeypatch.setattr(S, "find_expired_promos", multiple_promos)
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/nl/run", json={"text": "clean my promos"})
        
        assert r.status_code == 200
        j = r.json()
        assert j["count"] == 3
        assert len(j["proposed_actions"]) == 3
        
        # Check all actions are archive
        for action in j["proposed_actions"]:
            assert action["action"] == "archive"
            assert action["policy_id"] == "promo-expired-archive"
