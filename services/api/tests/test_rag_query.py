# services/api/tests/test_rag_query.py
"""
Tests for Phase 4 AI Feature: RAG Search
"""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestRagQueryEndpoint:
    """Test RAG search endpoint"""

    @patch("app.routers.rag.FEATURE_RAG_SEARCH", True)
    @patch("app.routers.rag.get_es_client")
    def test_rag_query_returns_results(self, mock_es_client):
        """Should return search results with highlights"""
        # Mock Elasticsearch response
        mock_es = MagicMock()
        mock_es.search.return_value = {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {
                        "_id": "msg-001",
                        "_score": 0.92,
                        "_source": {
                            "thread_id": "demo-1",
                            "message_id": "msg-001",
                            "sender": "bianca@techcorp.com",
                            "subject": "Interview Scheduling",
                            "date": "2025-01-14T09:00:00Z",
                        },
                        "highlight": {
                            "body_text": ["...initial <em>interview</em> scheduling..."]
                        },
                    },
                    {
                        "_id": "msg-002",
                        "_score": 0.88,
                        "_source": {
                            "thread_id": "demo-1",
                            "message_id": "msg-002",
                            "sender": "hiring@startup.io",
                            "subject": "Re: Interview",
                            "date": "2025-01-14T14:30:00Z",
                        },
                        "highlight": {"subject": ["Re: <em>Interview</em>"]},
                    },
                ],
            }
        }
        mock_es_client.return_value = mock_es

        response = client.post(
            "/api/rag/query", json={"q": "interview scheduling", "k": 5}
        )

        assert response.status_code == 200
        data = response.json()

        assert "hits" in data
        assert "total" in data
        assert len(data["hits"]) == 2
        assert data["total"] == 3

        # Check first hit structure
        hit = data["hits"][0]
        assert hit["thread_id"] == "demo-1"
        assert hit["message_id"] == "msg-001"
        assert hit["score"] == 0.92
        assert len(hit["highlights"]) > 0
        assert "<em>" in hit["highlights"][0]  # Has highlight tags

    @patch("app.routers.rag.FEATURE_RAG_SEARCH", True)
    @patch("app.routers.rag.get_es_client")
    def test_rag_query_falls_back_to_mock(self, mock_es_client):
        """Should fall back to mock data when ES is unavailable"""
        mock_es_client.return_value = None  # ES unavailable

        response = client.post("/api/rag/query", json={"q": "interview", "k": 3})

        assert response.status_code == 200
        data = response.json()

        # Should return mock data
        assert "hits" in data
        assert len(data["hits"]) <= 3  # Respects k parameter

    @patch("app.routers.rag.FEATURE_RAG_SEARCH", False)
    def test_rag_query_feature_disabled(self):
        """Should return 503 when feature is disabled"""
        response = client.post("/api/rag/query", json={"q": "test", "k": 5})

        assert response.status_code == 503
        assert "disabled" in response.json()["detail"].lower()

    @patch("app.routers.rag.FEATURE_RAG_SEARCH", True)
    def test_rag_query_validation(self):
        """Should validate request parameters"""
        # Empty query
        response = client.post("/api/rag/query", json={"q": "", "k": 5})
        assert response.status_code == 422  # Validation error

        # Query too long
        response = client.post("/api/rag/query", json={"q": "x" * 501, "k": 5})
        assert response.status_code == 422

        # k out of range
        response = client.post("/api/rag/query", json={"q": "test", "k": 0})
        assert response.status_code == 422

        response = client.post("/api/rag/query", json={"q": "test", "k": 21})
        assert response.status_code == 422

    @patch("app.routers.rag.FEATURE_RAG_SEARCH", True)
    @patch("app.routers.rag.get_es_client")
    def test_rag_query_respects_k_parameter(self, mock_es_client):
        """Should return at most k results"""
        mock_es = MagicMock()
        # Create 10 mock results
        mock_hits = [
            {
                "_id": f"msg-{i:03d}",
                "_score": 0.9 - (i * 0.05),
                "_source": {
                    "thread_id": "thread-1",
                    "message_id": f"msg-{i:03d}",
                    "sender": "test@example.com",
                    "subject": f"Email {i}",
                    "date": "2025-01-15T10:00:00Z",
                },
                "highlight": {"body_text": [f"match {i}"]},
            }
            for i in range(10)
        ]

        mock_es.search.return_value = {
            "hits": {
                "total": {"value": 10},
                "hits": mock_hits[:3],  # ES respects size parameter
            }
        }
        mock_es_client.return_value = mock_es

        response = client.post("/api/rag/query", json={"q": "test", "k": 3})

        assert response.status_code == 200
        data = response.json()
        assert len(data["hits"]) == 3

    @patch("app.routers.rag.FEATURE_RAG_SEARCH", True)
    @patch("app.routers.rag.get_es_client")
    def test_rag_query_handles_no_results(self, mock_es_client):
        """Should handle queries with no results"""
        mock_es = MagicMock()
        mock_es.search.return_value = {"hits": {"total": {"value": 0}, "hits": []}}
        mock_es_client.return_value = mock_es

        response = client.post(
            "/api/rag/query", json={"q": "nonexistent query xyz", "k": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["hits"] == []
        assert data["total"] == 0


class TestRagHealth:
    """Test RAG health endpoint"""

    @patch("app.routers.rag.get_es_client")
    def test_health_elasticsearch_available(self, mock_es_client):
        """Should report ES available"""
        mock_es_client.return_value = MagicMock()

        response = client.get("/api/rag/health")

        assert response.status_code == 200
        data = response.json()
        assert data["elasticsearch_available"] is True
        assert data["fallback_mode"] == "live"

    @patch("app.routers.rag.get_es_client")
    def test_health_elasticsearch_unavailable(self, mock_es_client):
        """Should report ES unavailable and fallback mode"""
        mock_es_client.return_value = None

        response = client.get("/api/rag/health")

        assert response.status_code == 200
        data = response.json()
        assert data["elasticsearch_available"] is False
        assert data["fallback_mode"] == "mock"
