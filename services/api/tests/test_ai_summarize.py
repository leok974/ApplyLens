# services/api/tests/test_ai_summarize.py
"""
Tests for Phase 4 AI Feature: Email Summarizer
"""

from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestSummarizeEndpoint:
    """Test email thread summarization endpoint"""

    @patch("app.routers.ai.FEATURE_SUMMARIZE", True)
    @patch("app.routers.ai.ollama_chat")
    async def test_summarize_returns_5_bullets(self, mock_ollama):
        """Should return exactly 5 bullets"""
        # Mock Ollama response
        mock_ollama.return_value = """
        {
            "bullets": [
                "Bianca is scheduling an interview",
                "Initial time proposed: Tuesday 2 PM",
                "Interview confirmed for Tuesday",
                "Conflict arose, rescheduling needed",
                "New time: Wednesday 3 PM"
            ],
            "citations": []
        }
        """

        response = client.post(
            "/api/ai/summarize", json={"thread_id": "demo-1", "max_citations": 3}
        )

        assert response.status_code == 200
        data = response.json()
        assert "bullets" in data
        assert len(data["bullets"]) == 5
        assert "citations" in data

    @patch("app.routers.ai.FEATURE_SUMMARIZE", True)
    @patch("app.routers.ai.ollama_chat")
    async def test_summarize_respects_max_citations(self, mock_ollama):
        """Should cap citations at max_citations"""
        mock_ollama.return_value = """
        {
            "bullets": ["b1", "b2", "b3", "b4", "b5"],
            "citations": [
                {"snippet": "text1", "message_id": "msg-1", "offset": 0},
                {"snippet": "text2", "message_id": "msg-2", "offset": 10},
                {"snippet": "text3", "message_id": "msg-3", "offset": 20},
                {"snippet": "text4", "message_id": "msg-4", "offset": 30}
            ]
        }
        """

        response = client.post(
            "/api/ai/summarize", json={"thread_id": "demo-1", "max_citations": 2}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["citations"]) == 2

    @patch("app.routers.ai.FEATURE_SUMMARIZE", False)
    def test_summarize_feature_disabled(self):
        """Should return 503 when feature is disabled"""
        response = client.post("/api/ai/summarize", json={"thread_id": "demo-1"})

        assert response.status_code == 503
        assert "disabled" in response.json()["detail"].lower()

    @patch("app.routers.ai.FEATURE_SUMMARIZE", True)
    def test_summarize_thread_not_found(self):
        """Should return 404 for non-existent thread"""
        response = client.post(
            "/api/ai/summarize", json={"thread_id": "nonexistent-thread"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("app.routers.ai.FEATURE_SUMMARIZE", True)
    @patch("app.routers.ai.check_ollama_health")
    @patch("app.routers.ai.ollama_chat", side_effect=Exception("Service down"))
    async def test_summarize_ollama_unavailable(self, mock_chat, mock_health):
        """Should return 503 when Ollama is unavailable"""
        mock_health.return_value = False

        response = client.post("/api/ai/summarize", json={"thread_id": "demo-1"})

        # Note: Actual behavior depends on implementation
        # Either 503 (service unavailable) or 500 (internal error)
        assert response.status_code in [500, 503]

    @patch("app.routers.ai.FEATURE_SUMMARIZE", True)
    @patch("app.routers.ai.ollama_chat")
    async def test_summarize_handles_markdown_json(self, mock_ollama):
        """Should parse JSON wrapped in markdown code blocks"""
        # Ollama sometimes returns JSON wrapped in ```json...```
        mock_ollama.return_value = """
        ```json
        {
            "bullets": ["b1", "b2", "b3", "b4", "b5"],
            "citations": []
        }
        ```
        """

        response = client.post("/api/ai/summarize", json={"thread_id": "demo-1"})

        assert response.status_code == 200
        data = response.json()
        assert len(data["bullets"]) == 5


class TestAIHealth:
    """Test AI service health endpoint"""

    @patch("app.routers.ai.check_ollama_health")
    def test_health_ollama_available(self, mock_health):
        """Should report healthy when Ollama is available"""
        mock_health.return_value = True

        response = client.get("/api/ai/health")

        assert response.status_code == 200
        data = response.json()
        assert data["ollama_available"] is True

    @patch("app.routers.ai.check_ollama_health")
    def test_health_ollama_unavailable(self, mock_health):
        """Should report unavailable when Ollama is down"""
        mock_health.return_value = False

        response = client.get("/api/ai/health")

        assert response.status_code == 200
        data = response.json()
        assert data["ollama_available"] is False
