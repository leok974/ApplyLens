"""
Unit Tests for Unsubscribe Logic

Tests RFC-2369 List-Unsubscribe header parsing and HTTP execution.
"""

from app.logic.unsubscribe import parse_list_unsubscribe, perform_unsubscribe


class TestUnsubscribeHeaderParsing:
    """Test List-Unsubscribe header parsing."""
    
    def test_parse_both_targets(self):
        """Test parsing both mailto and HTTP targets."""
        headers = {
            "List-Unsubscribe": "<mailto:unsub@ex.com>, <https://ex.com/unsub?id=123>"
        }
        mailto, http = parse_list_unsubscribe(headers)
        
        assert mailto == "unsub@ex.com"
        assert http == "https://ex.com/unsub?id=123"
    
    def test_parse_http_only(self):
        """Test parsing HTTP target only."""
        headers = {
            "List-Unsubscribe": "<https://example.com/unsub>"
        }
        mailto, http = parse_list_unsubscribe(headers)
        
        assert mailto is None
        assert http == "https://example.com/unsub"
    
    def test_parse_mailto_only(self):
        """Test parsing mailto target only."""
        headers = {
            "List-Unsubscribe": "<mailto:unsubscribe@example.com>"
        }
        mailto, http = parse_list_unsubscribe(headers)
        
        assert mailto == "unsubscribe@example.com"
        assert http is None
    
    def test_parse_case_insensitive(self):
        """Test that header parsing is case-insensitive."""
        headers = {
            "list-unsubscribe": "<mailto:unsub@ex.com>"
        }
        mailto, http = parse_list_unsubscribe(headers)
        
        assert mailto == "unsub@ex.com"
    
    def test_parse_empty_headers(self):
        """Test parsing with no headers."""
        mailto, http = parse_list_unsubscribe({})
        
        assert mailto is None
        assert http is None
    
    def test_parse_no_unsubscribe_header(self):
        """Test parsing with other headers but no List-Unsubscribe."""
        headers = {
            "Subject": "Test email",
            "From": "sender@example.com"
        }
        mailto, http = parse_list_unsubscribe(headers)
        
        assert mailto is None
        assert http is None


class TestUnsubscribeExecution:
    """Test unsubscribe execution logic."""
    
    def test_http_unsubscribe_exec(self, monkeypatch):
        """Test HTTP unsubscribe execution."""
        calls = {"get": 0, "head": 0}
        
        class MockResponse:
            status_code = 200
        
        import app.logic.unsubscribe as u
        
        def mock_head(*args, **kwargs):
            calls["head"] += 1
            return MockResponse()
        
        def mock_get(*args, **kwargs):
            calls["get"] += 1
            return MockResponse()
        
        monkeypatch.setattr(u.requests, "head", mock_head)
        monkeypatch.setattr(u.requests, "get", mock_get)
        
        res = perform_unsubscribe({"List-Unsubscribe": "<https://ex.com/unsub>"})
        
        assert res["performed"] == "http"
        assert res["status"] == 200
        assert calls["head"] == 1  # Should try HEAD first
    
    def test_http_unsubscribe_fallback_to_get(self, monkeypatch):
        """Test that HTTP unsubscribe falls back to GET if HEAD fails."""
        calls = {"get": 0, "head": 0}
        
        class MockResponse:
            status_code = 200
        
        import app.logic.unsubscribe as u
        
        def mock_head(*args, **kwargs):
            calls["head"] += 1
            raise Exception("HEAD failed")
        
        def mock_get(*args, **kwargs):
            calls["get"] += 1
            return MockResponse()
        
        monkeypatch.setattr(u.requests, "head", mock_head)
        monkeypatch.setattr(u.requests, "get", mock_get)
        
        res = perform_unsubscribe({"List-Unsubscribe": "<https://ex.com/unsub>"})
        
        assert res["performed"] == "http"
        assert res["status"] == 200
        assert calls["head"] == 1
        assert calls["get"] == 1  # Should fall back to GET
    
    def test_mailto_unsubscribe_queued(self):
        """Test that mailto unsubscribe is queued."""
        res = perform_unsubscribe({
            "List-Unsubscribe": "<mailto:unsub@example.com>"
        })
        
        assert res["performed"] == "mailto"
        assert res["status"] == "queued"
        assert res["mailto"] == "unsub@example.com"
    
    def test_http_preferred_over_mailto(self, monkeypatch):
        """Test that HTTP unsubscribe is preferred over mailto."""
        class MockResponse:
            status_code = 204
        
        import app.logic.unsubscribe as u
        monkeypatch.setattr(u.requests, "head", lambda *a, **k: MockResponse())
        
        res = perform_unsubscribe({
            "List-Unsubscribe": "<mailto:unsub@ex.com>, <https://ex.com/unsub>"
        })
        
        # Should use HTTP, not mailto
        assert res["performed"] == "http"
        assert res["status"] == 204
    
    def test_no_targets_available(self):
        """Test behavior when no unsubscribe targets are available."""
        res = perform_unsubscribe({
            "Subject": "Test email"
        })
        
        assert res["performed"] is None
        assert res["status"] is None
        assert res["mailto"] is None
        assert res["http"] is None
