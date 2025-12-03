"""
Tests for email classifier diagnostics endpoints.
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_classifier_health_endpoint_structure():
    """Test that /diagnostics/classifier/health returns expected JSON structure."""
    response = client.get("/diagnostics/classifier/health")

    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "ok" in data
    assert "status" in data
    assert "mode" in data
    assert "model_version" in data
    assert "has_model_artifacts" in data
    assert "uses_ml" in data
    assert "message" in data

    # Check types
    assert isinstance(data["ok"], bool)
    assert isinstance(data["status"], str)
    assert isinstance(data["mode"], str)
    assert isinstance(data["model_version"], str)
    assert isinstance(data["has_model_artifacts"], bool)
    assert isinstance(data["uses_ml"], bool)
    assert isinstance(data["message"], str)

    # Status should be one of expected values
    assert data["status"] in ["healthy", "degraded", "unhealthy"]

    # Mode should be one of expected values
    assert data["mode"] in ["heuristic", "ml_shadow", "ml_live", "unknown"]


def test_classifier_health_heuristic_mode():
    """Test health check in heuristic mode (default, no ML required)."""
    response = client.get("/diagnostics/classifier/health")

    assert response.status_code == 200
    data = response.json()

    # In heuristic mode without ML artifacts, should still be healthy
    if data["mode"] == "heuristic":
        assert data["ok"] is True or data["status"] == "healthy"
        assert data["uses_ml"] is False
        assert "heuristic" in data["message"].lower()


def test_classifier_health_sample_prediction():
    """Test that health check includes a sample prediction."""
    response = client.get("/diagnostics/classifier/health")

    assert response.status_code == 200
    data = response.json()

    # Sample prediction should be present if classifier is healthy
    if data["ok"]:
        assert "sample_prediction" in data
        assert data["sample_prediction"] is not None

        prediction = data["sample_prediction"]
        assert "category" in prediction
        assert "is_real_opportunity" in prediction
        assert "confidence" in prediction
        assert "source" in prediction

        # Confidence should be between 0 and 1
        assert 0 <= prediction["confidence"] <= 1

        # is_real_opportunity should be boolean
        assert isinstance(prediction["is_real_opportunity"], bool)


def test_classifier_health_no_auth_required():
    """Test that classifier health check doesn't require authentication."""
    # This endpoint should work without auth for monitoring purposes
    response = client.get("/diagnostics/classifier/health")

    # Should not return 401/403
    assert response.status_code == 200


def test_classifier_reload_endpoint():
    """Test classifier reload endpoint exists and returns expected structure."""
    response = client.post("/diagnostics/classifier/reload")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] in ["reloaded", "error"]

    if data["status"] == "reloaded":
        assert "mode" in data
        assert "model_version" in data
        assert "ml_model_loaded" in data
