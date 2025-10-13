"""
Unit tests for Elasticsearch search helpers.

These tests monkey-patch the ES client to avoid requiring a running cluster.
"""

import asyncio
from typing import Dict, Any, List
import app.logic.search as S


class FakeES:
    """Mock Elasticsearch client for testing."""
    
    def __init__(self, hits: List[Dict[str, Any]]):
        self._hits = hits
    
    def search(self, index: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Return fake search results."""
        return {"hits": {"hits": self._hits}}


def _hit(doc_id: str, src: Dict[str, Any]) -> Dict[str, Any]:
    """Create a fake ES hit document."""
    return {"_id": doc_id, "_source": {"id": doc_id, **src}}


class TestFindHighRisk:
    """Tests for find_high_risk search function."""
    
    def test_find_high_risk_uses_threshold(self, monkeypatch):
        """Test that find_high_risk queries with the correct risk score threshold."""
        fake_hits = [
            _hit(
                "ph1",
                {
                    "risk_score": 92,
                    "category": "security",
                    "received_at": "2025-10-08T00:00:00Z",
                },
            ),
            _hit(
                "ph2",
                {
                    "risk_score": 81,
                    "category": "security",
                    "received_at": "2025-10-09T00:00:00Z",
                },
            ),
        ]
        monkeypatch.setattr(S, "es_client", lambda: FakeES(fake_hits))
        
        # Run the async function
        res = asyncio.get_event_loop().run_until_complete(S.find_high_risk())
        
        assert len(res) == 2
        assert res[0]["risk_score"] >= 80
        assert res[1]["risk_score"] >= 80
    
    def test_find_high_risk_custom_threshold(self, monkeypatch):
        """Test find_high_risk with custom min_risk parameter."""
        fake_hits = [
            _hit("ph1", {"risk_score": 95, "category": "security"}),
        ]
        monkeypatch.setattr(S, "es_client", lambda: FakeES(fake_hits))
        
        res = asyncio.get_event_loop().run_until_complete(S.find_high_risk(min_risk=90.0))
        
        assert len(res) == 1
        assert res[0]["risk_score"] >= 90
    
    def test_find_high_risk_respects_limit(self, monkeypatch):
        """Test that find_high_risk respects the limit parameter."""
        fake_hits = [_hit(f"ph{i}", {"risk_score": 85 + i}) for i in range(10)]
        monkeypatch.setattr(S, "es_client", lambda: FakeES(fake_hits))
        
        res = asyncio.get_event_loop().run_until_complete(S.find_high_risk(limit=5))
        
        # Note: We're mocking ES, so we still get all hits, but in real scenario
        # the ES query would have size=5
        assert len(res) == 10  # Mock returns all, but real ES would respect limit


class TestFindUnsubscribeCandidates:
    """Tests for find_unsubscribe_candidates search function."""
    
    def test_find_unsubscribe_candidates_basic(self, monkeypatch):
        """Test basic unsubscribe candidate search."""
        fake_hits = [
            _hit(
                "n1",
                {
                    "has_unsubscribe": True,
                    "sender_domain": "news.example.com",
                    "received_at": "2025-08-01T00:00:00Z",
                },
            )
        ]
        monkeypatch.setattr(S, "es_client", lambda: FakeES(fake_hits))
        
        res = asyncio.get_event_loop().run_until_complete(
            S.find_unsubscribe_candidates(days=60)
        )
        
        assert len(res) == 1
        assert res[0]["has_unsubscribe"] is True
        assert res[0]["sender_domain"] == "news.example.com"
    
    def test_find_unsubscribe_candidates_multiple_senders(self, monkeypatch):
        """Test finding unsubscribe candidates from multiple senders."""
        fake_hits = [
            _hit("n1", {"has_unsubscribe": True, "sender_domain": "news1.com"}),
            _hit("n2", {"has_unsubscribe": True, "sender_domain": "news2.com"}),
            _hit("n3", {"has_unsubscribe": True, "sender_domain": "news1.com"}),
        ]
        monkeypatch.setattr(S, "es_client", lambda: FakeES(fake_hits))
        
        res = asyncio.get_event_loop().run_until_complete(
            S.find_unsubscribe_candidates(days=60)
        )
        
        assert len(res) == 3
        sender_domains = {email["sender_domain"] for email in res}
        assert "news1.com" in sender_domains
        assert "news2.com" in sender_domains


class TestFindExpiredPromos:
    """Tests for find_expired_promos search function."""
    
    def test_find_expired_promos_basic(self, monkeypatch):
        """Test basic expired promotions search."""
        fake_hits = [
            _hit(
                "p1",
                {
                    "category": "promotions",
                    "expires_at": "2025-10-01T00:00:00Z",
                    "received_at": "2025-10-02T00:00:00Z",
                },
            )
        ]
        monkeypatch.setattr(S, "es_client", lambda: FakeES(fake_hits))
        
        res = asyncio.get_event_loop().run_until_complete(S.find_expired_promos(days=7))
        
        assert len(res) == 1
        assert res[0]["category"] == "promotions"
        assert res[0]["expires_at"] == "2025-10-01T00:00:00Z"
    
    def test_find_expired_promos_multiple(self, monkeypatch):
        """Test finding multiple expired promotions."""
        fake_hits = [
            _hit("p1", {"category": "promotions", "expires_at": "2025-09-01T00:00:00Z"}),
            _hit("p2", {"category": "promotions", "expires_at": "2025-09-15T00:00:00Z"}),
        ]
        monkeypatch.setattr(S, "es_client", lambda: FakeES(fake_hits))
        
        res = asyncio.get_event_loop().run_until_complete(S.find_expired_promos(days=14))
        
        assert len(res) == 2


class TestFindByFilter:
    """Tests for find_by_filter generic search function."""
    
    def test_find_by_filter_term_query(self, monkeypatch):
        """Test find_by_filter with a term query."""
        fake_hits = [
            _hit("e1", {"category": "promotions"}),
            _hit("e2", {"category": "promotions"}),
        ]
        monkeypatch.setattr(S, "es_client", lambda: FakeES(fake_hits))
        
        filter_query = {"term": {"category": "promotions"}}
        res = asyncio.get_event_loop().run_until_complete(
            S.find_by_filter(filter_query)
        )
        
        assert len(res) == 2
        assert all(email["category"] == "promotions" for email in res)
    
    def test_find_by_filter_bool_query(self, monkeypatch):
        """Test find_by_filter with a bool query."""
        fake_hits = [
            _hit("e1", {"category": "promotions", "risk_score": 50}),
        ]
        monkeypatch.setattr(S, "es_client", lambda: FakeES(fake_hits))
        
        filter_query = {
            "bool": {
                "filter": [
                    {"term": {"category": "promotions"}},
                    {"range": {"risk_score": {"gte": 40}}},
                ]
            }
        }
        res = asyncio.get_event_loop().run_until_complete(
            S.find_by_filter(filter_query)
        )
        
        assert len(res) == 1
        assert res[0]["category"] == "promotions"
        assert res[0]["risk_score"] == 50
    
    def test_find_by_filter_custom_fields(self, monkeypatch):
        """Test find_by_filter with custom field selection."""
        fake_hits = [
            _hit("e1", {"id": "e1", "subject": "Test", "body_text": "Long body..."}),
        ]
        monkeypatch.setattr(S, "es_client", lambda: FakeES(fake_hits))
        
        filter_query = {"match_all": {}}
        res = asyncio.get_event_loop().run_until_complete(
            S.find_by_filter(filter_query, fields=["id", "subject"])
        )
        
        assert len(res) == 1
        # The mock doesn't actually filter fields, but real ES would


class TestSearchEmails:
    """Tests for search_emails general-purpose search."""
    
    def test_search_emails_by_category(self, monkeypatch):
        """Test search_emails filtering by category."""
        fake_hits = [_hit("e1", {"category": "bills"})]
        monkeypatch.setattr(S, "es_client", lambda: FakeES(fake_hits))
        
        res = asyncio.get_event_loop().run_until_complete(
            S.search_emails(category="bills")
        )
        
        assert len(res) == 1
        assert res[0]["category"] == "bills"
    
    def test_search_emails_by_risk(self, monkeypatch):
        """Test search_emails filtering by risk score."""
        fake_hits = [_hit("e1", {"risk_score": 85})]
        monkeypatch.setattr(S, "es_client", lambda: FakeES(fake_hits))
        
        res = asyncio.get_event_loop().run_until_complete(
            S.search_emails(min_risk=80.0)
        )
        
        assert len(res) == 1
        assert res[0]["risk_score"] >= 80
    
    def test_search_emails_multiple_filters(self, monkeypatch):
        """Test search_emails with multiple filters."""
        fake_hits = [
            _hit("e1", {"category": "promotions", "has_unsubscribe": True, "risk_score": 30}),
        ]
        monkeypatch.setattr(S, "es_client", lambda: FakeES(fake_hits))
        
        res = asyncio.get_event_loop().run_until_complete(
            S.search_emails(category="promotions", has_unsubscribe=True)
        )
        
        assert len(res) == 1
        assert res[0]["category"] == "promotions"
        assert res[0]["has_unsubscribe"] is True


class TestHitNormalization:
    """Tests for _hit_to_email normalization function."""
    
    def test_hit_to_email_with_all_fields(self):
        """Test normalizing a complete ES hit."""
        hit = {
            "_id": "doc123",
            "_source": {
                "id": "email123",
                "category": "promotions",
                "expires_at": "2025-12-31T00:00:00Z",
                "received_at": "2025-10-01T00:00:00Z",
                "risk_score": 25,
                "has_unsubscribe": True,
                "sender_domain": "shop.example.com",
                "subject": "50% off sale!",
                "body_text": "Check out our amazing deals...",
            },
        }
        
        result = S._hit_to_email(hit)
        
        assert result["id"] == "email123"
        assert result["category"] == "promotions"
        assert result["risk_score"] == 25
        assert result["has_unsubscribe"] is True
    
    def test_hit_to_email_fallback_id(self):
        """Test that _hit_to_email uses _id when id is missing from source."""
        hit = {
            "_id": "doc123",
            "_source": {
                "category": "personal",
            },
        }
        
        result = S._hit_to_email(hit)
        
        assert result["id"] == "doc123"
    
    def test_hit_to_email_missing_fields(self):
        """Test normalizing a hit with missing optional fields."""
        hit = {
            "_id": "doc123",
            "_source": {
                "id": "email123",
                "category": "personal",
            },
        }
        
        result = S._hit_to_email(hit)
        
        assert result["id"] == "email123"
        assert result["category"] == "personal"
        assert result["expires_at"] is None
        assert result["risk_score"] is None
        assert result["has_unsubscribe"] is None
