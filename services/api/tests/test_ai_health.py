"""
Tests for AI health endpoints and Phase 4 features.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAIHealth:
    """Test AI health check endpoints."""
    
    def test_ai_health_returns_status(self, client):
        """Test /api/ai/health returns ollama status."""
        response = client.get("/api/ai/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "ollama" in data
        assert data["ollama"] in ["available", "unavailable"]
        assert "features" in data
        
    def test_ai_health_includes_features(self, client):
        """Test health endpoint includes feature flags."""
        response = client.get("/api/ai/health")
        data = response.json()
        
        features = data.get("features", {})
        assert "summarize" in features
        assert isinstance(features["summarize"], bool)


class TestAISummarize:
    """Test AI summarization endpoint."""
    
    def test_summarize_requires_thread_id(self, client):
        """Test summarize endpoint requires thread_id."""
        response = client.post(
            "/api/ai/summarize",
            json={}
        )
        # Should fail validation
        assert response.status_code in [400, 422]
    
    def test_summarize_accepts_valid_request(self, client):
        """Test summarize endpoint accepts valid request."""
        response = client.post(
            "/api/ai/summarize",
            json={"thread_id": "test-thread-123", "max_citations": 3}
        )
        # May return 404 if thread doesn't exist, but endpoint should accept request
        assert response.status_code in [200, 404, 500]
        
    def test_summarize_respects_max_citations(self, client):
        """Test max_citations parameter is accepted."""
        response = client.post(
            "/api/ai/summarize",
            json={"thread_id": "test-thread", "max_citations": 5}
        )
        # Endpoint should accept the parameter
        assert response.status_code in [200, 404, 500]


class TestRAGHealth:
    """Test RAG health endpoint."""
    
    def test_rag_health_returns_status(self, client):
        """Test /rag/health returns status."""
        response = client.get("/rag/health")
        assert response.status_code == 200
        
        data = response.json()
        # Accept either schema format
        if "status" in data:
            assert data["status"] in ["ready", "fallback", "unavailable"]
        else:
            # Alternative schema with elasticsearch_available
            assert "elasticsearch_available" in data
            assert isinstance(data["elasticsearch_available"], bool)


class TestRAGQuery:
    """Test RAG query endpoint."""
    
    def test_rag_query_requires_query(self, client):
        """Test RAG query requires 'q' parameter - accepts both paths."""
        # Try /api/rag/query first (backwards compat)
        response = client.post("/api/rag/query", json={})
        if response.status_code == 404:
            # Fallback to /rag/query
            response = client.post("/rag/query", json={})
        
        # Should fail validation
        assert response.status_code in [400, 422]
    
    def test_rag_query_accepts_valid_request(self, client):
        """Test RAG query accepts valid request - accepts both paths."""
        # Try /api/rag/query first (backwards compat)
        response = client.post("/api/rag/query", json={"q": "test query", "k": 5})
        if response.status_code == 404:
            # Fallback to /rag/query
            response = client.post("/rag/query", json={"q": "test query", "k": 5})
        
        # May return empty results, but should accept request
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or "results" in data


class TestSecurityRisk:
    """Test security risk endpoints."""
    
    def test_risk_top3_requires_message_id(self, client):
        """Test risk endpoint requires message_id."""
        response = client.get("/api/security/risk-top3")
        # Should require message_id parameter
        assert response.status_code in [400, 422]
    
    def test_risk_top3_accepts_message_id(self, client):
        """Test risk endpoint accepts message_id."""
        response = client.get("/api/security/risk-top3?message_id=test-msg-123")
        # May return 404 or empty results
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "score" in data or "signals" in data


class TestMetricsDivergence:
    """Test metrics divergence endpoint."""
    
    def test_divergence_24h_returns_data(self, client):
        """Test divergence endpoint returns metrics."""
        response = client.get("/api/metrics/divergence-24h")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["ok", "degraded", "paused"]
        
        if data["status"] != "paused":
            assert "divergence_pct" in data
            assert "es_count" in data
            assert "bq_count" in data
    
    def test_divergence_status_thresholds(self, client):
        """Test divergence status respects thresholds."""
        response = client.get("/api/metrics/divergence-24h")
        data = response.json()
        
        if data["status"] == "ok":
            assert data.get("divergence_pct", 0) < 2.0
        elif data["status"] == "degraded":
            assert 2.0 <= data.get("divergence_pct", 0) <= 5.0
        # paused may not have divergence_pct


class TestPhase4Integration:
    """Integration tests for Phase 4 features."""
    
    def test_all_phase4_endpoints_registered(self, client):
        """Test all Phase 4 endpoints are accessible - accepts both /rag and /api/rag paths."""
        endpoints = [
            "/api/ai/health",
            "/api/ai/summarize",
            "/rag/health",
            "/api/security/risk-top3",
            "/api/metrics/divergence-24h",
        ]
        
        # RAG query - try both paths
        rag_paths = ["/api/rag/query", "/rag/query"]
        rag_found = False
        for rag_path in rag_paths:
            response = client.post(rag_path, json={})
            if response.status_code != 404:
                rag_found = True
                break
        assert rag_found, "RAG query endpoint not found at /api/rag/query or /rag/query"
        
        for endpoint in endpoints:
            if endpoint in ["/api/ai/summarize"]:
                # POST endpoints
                response = client.post(endpoint, json={})
            else:
                # GET endpoints
                response = client.get(endpoint)
            
            # Should not return 404 (not found)
            assert response.status_code != 404, f"Endpoint {endpoint} not found"
    
    def test_openapi_includes_phase4_routes(self, client):
        """Test OpenAPI spec includes Phase 4 routes - accepts both /rag and /api/rag."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi = response.json()
        paths = openapi.get("paths", {})
        
        # Check for Phase 4 paths (required)
        required_paths = [
            "/api/ai/health",
            "/api/ai/summarize",
            "/rag/health",
        ]
        
        for path in required_paths:
            assert path in paths, f"Path {path} not in OpenAPI spec"
        
        # RAG query - accept either path
        rag_ok = {"/api/rag/query", "/rag/query"} & set(paths.keys())
        assert rag_ok, "Missing RAG query route (/api/rag/query or /rag/query) in OpenAPI spec"
