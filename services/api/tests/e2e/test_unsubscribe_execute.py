"""
E2E Tests for Unsubscribe Execution

Tests the complete unsubscribe workflow including preview and execute endpoints.
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_unsubscribe_preview_with_http():
    """Test previewing unsubscribe with HTTP target."""
    payload = {
        "email_id": "e1",
        "headers": {
            "List-Unsubscribe": "<https://example.com/unsub?x=1>"
        }
    }
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/unsubscribe/preview", json=payload)
        
        assert r.status_code == 200
        j = r.json()
        assert j["email_id"] == "e1"
        assert j["result"]["http"] == "https://example.com/unsub?x=1"
        assert j["result"]["performed"] is None  # Preview doesn't execute


@pytest.mark.asyncio
async def test_unsubscribe_preview_with_both_targets():
    """Test previewing unsubscribe with both mailto and HTTP targets."""
    payload = {
        "email_id": "e2",
        "headers": {
            "List-Unsubscribe": "<mailto:unsub@ex.com>, <https://ex.com/unsub>"
        }
    }
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/unsubscribe/preview", json=payload)
        
        assert r.status_code == 200
        j = r.json()
        assert j["result"]["mailto"] == "unsub@ex.com"
        assert j["result"]["http"] == "https://ex.com/unsub"
        assert j["result"]["performed"] is None


@pytest.mark.asyncio
async def test_unsubscribe_execute_with_http(monkeypatch):
    """Test executing unsubscribe with HTTP target."""
    class MockResponse:
        status_code = 204
    
    # Mock HTTP requests
    import app.logic.unsubscribe as u
    monkeypatch.setattr(u.requests, "head", lambda *a, **k: MockResponse())
    monkeypatch.setattr(u.requests, "get", lambda *a, **k: MockResponse())
    
    # Stub audit_action to avoid DB writes
    import app.routers.unsubscribe as R
    audit_calls = []
    def mock_audit(**kwargs):
        audit_calls.append(kwargs)
    monkeypatch.setattr(R, "audit_action", mock_audit)
    
    payload = {
        "email_id": "e1",
        "headers": {
            "List-Unsubscribe": "<https://example.com/unsub?x=1>"
        }
    }
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/unsubscribe/execute", json=payload)
        
        assert r.status_code == 200
        j = r.json()
        assert j["result"]["performed"] == "http"
        assert j["result"]["status"] in (200, 204)
        
        # Check audit was called
        assert len(audit_calls) == 1
        assert audit_calls[0]["email_id"] == "e1"
        assert audit_calls[0]["action"] == "unsubscribe"


@pytest.mark.asyncio
async def test_unsubscribe_execute_with_mailto(monkeypatch):
    """Test executing unsubscribe with mailto target."""
    # Stub audit_action
    import app.routers.unsubscribe as R
    audit_calls = []
    monkeypatch.setattr(R, "audit_action", lambda **k: audit_calls.append(k))
    
    payload = {
        "email_id": "e2",
        "headers": {
            "List-Unsubscribe": "<mailto:unsub@example.com>"
        }
    }
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/unsubscribe/execute", json=payload)
        
        assert r.status_code == 200
        j = r.json()
        assert j["result"]["performed"] == "mailto"
        assert j["result"]["status"] == "queued"
        
        # Check audit
        assert len(audit_calls) == 1
        assert audit_calls[0]["action"] == "unsubscribe"


@pytest.mark.asyncio
async def test_unsubscribe_execute_no_targets(monkeypatch):
    """Test executing unsubscribe with no targets fails."""
    # Stub audit_action
    import app.routers.unsubscribe as R
    monkeypatch.setattr(R, "audit_action", lambda **k: None)
    
    payload = {
        "email_id": "e3",
        "headers": {
            "Subject": "No unsubscribe header"
        }
    }
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/unsubscribe/execute", json=payload)
        
        assert r.status_code == 400
        assert "No List-Unsubscribe targets found" in r.json()["detail"]


@pytest.mark.asyncio
async def test_unsubscribe_preview_vs_execute_difference(monkeypatch):
    """Test that preview doesn't execute but execute does."""
    class MockResponse:
        status_code = 200
    
    http_calls = []
    
    import app.logic.unsubscribe as u
    def track_head(*args, **kwargs):
        http_calls.append("head")
        return MockResponse()
    def track_get(*args, **kwargs):
        http_calls.append("get")
        return MockResponse()
    
    monkeypatch.setattr(u.requests, "head", track_head)
    monkeypatch.setattr(u.requests, "get", track_get)
    
    # Stub audit
    import app.routers.unsubscribe as R
    monkeypatch.setattr(R, "audit_action", lambda **k: None)
    
    payload = {
        "email_id": "e1",
        "headers": {
            "List-Unsubscribe": "<https://example.com/unsub>"
        }
    }
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Preview should not make HTTP calls
        r_prev = await ac.post("/unsubscribe/preview", json=payload)
        assert r_prev.status_code == 200
        assert len(http_calls) == 0  # No HTTP calls made
        
        # Execute should make HTTP calls
        r_exec = await ac.post("/unsubscribe/execute", json=payload)
        assert r_exec.status_code == 200
        assert len(http_calls) > 0  # HTTP calls made
