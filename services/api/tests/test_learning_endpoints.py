"""Tests for companion learning endpoints.

These tests mirror the pattern from test_extension_endpoints.py:
- Use simple TestClient without auth mocking
- Rely on APPLYLENS_DEV=1 env var (set by pytest.ini)
- Test endpoint behavior, not authentication
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_learning_sync_accepts_valid_payload():
    """POST /api/extension/learning/sync should accept valid learning events."""
    payload = {
        "host": "jobs.lever.co",
        "schema_hash": "abc123def456",
        "events": [
            {
                "host": "jobs.lever.co",
                "schema_hash": "abc123def456",
                "suggested_map": {
                    "input[name='firstName']": "first_name",
                    "input[name='email']": "email",
                },
                "final_map": {
                    "input[name='firstName']": "first_name",
                    "input[name='email']": "email",
                },
                "edit_stats": {
                    "total_chars_added": 5,
                    "total_chars_deleted": 2,
                    "per_field": {
                        "input[name='firstName']": {"added": 5, "deleted": 2}
                    },
                },
                "duration_ms": 120000,
                "validation_errors": {},
                "status": "ok",
            }
        ],
    }

    r = client.post("/api/extension/learning/sync", json=payload)

    # Phase 1.0 stub returns 202 Accepted
    assert r.status_code == 202
    data = r.json()
    assert data.get("status") == "accepted"


def test_learning_profile_returns_response():
    """GET /api/extension/learning/profile should return profile structure."""
    r = client.get(
        "/api/extension/learning/profile",
        params={"host": "jobs.lever.co", "schema_hash": "abc123"},
    )

    assert r.status_code == 200
    data = r.json()

    # Verify response structure
    assert "host" in data
    assert "schema_hash" in data
    assert "canonical_map" in data
    assert "style_hint" in data

    # Phase 1.0 stub returns empty canonical_map
    assert data["host"] == "jobs.lever.co"
    assert data["schema_hash"] == "abc123"
    assert data["canonical_map"] == {}
    assert data["style_hint"] is None


def test_learning_sync_handles_multiple_events():
    """POST /api/extension/learning/sync should accept batch of multiple events."""
    payload = {
        "host": "apply.workday.com",
        "schema_hash": "workday_v2",
        "events": [
            {
                "host": "apply.workday.com",
                "schema_hash": "workday_v2",
                "suggested_map": {"input[name='q1']": "first_name"},
                "final_map": {"input[name='q1']": "first_name"},
                "edit_stats": {
                    "total_chars_added": 0,
                    "total_chars_deleted": 0,
                    "per_field": {},
                },
                "duration_ms": 8000,
                "validation_errors": {},
                "status": "ok",
            },
            {
                "host": "apply.workday.com",
                "schema_hash": "workday_v2",
                "suggested_map": {"input[name='q2']": "email"},
                "final_map": {"input[name='q2']": "email"},
                "edit_stats": {
                    "total_chars_added": 0,
                    "total_chars_deleted": 0,
                    "per_field": {},
                },
                "duration_ms": 12000,
                "validation_errors": {},
                "status": "ok",
            },
        ],
    }

    r = client.post("/api/extension/learning/sync", json=payload)
    assert r.status_code == 202
    data = r.json()
    assert data.get("status") == "accepted"


def test_learning_sync_validates_schema():
    """POST /api/extension/learning/sync should validate request schema."""
    # Missing required 'events' field
    invalid_payload = {"host": "jobs.lever.co", "schema_hash": "abc123"}

    r = client.post("/api/extension/learning/sync", json=invalid_payload)
    assert r.status_code == 422  # Unprocessable Entity

    # Verify error details
    data = r.json()
    assert "detail" in data


def test_learning_sync_increments_metric():
    """POST /api/extension/learning/sync should increment Prometheus counter."""
    from app.core.metrics import learning_sync_counter

    # Get initial count
    initial_count = learning_sync_counter.labels(status="stub")._value._value

    payload = {
        "host": "jobs.greenhouse.io",
        "schema_hash": "xyz789",
        "events": [
            {
                "host": "jobs.greenhouse.io",
                "schema_hash": "xyz789",
                "suggested_map": {},
                "final_map": {},
                "edit_stats": {
                    "total_chars_added": 0,
                    "total_chars_deleted": 0,
                    "per_field": {},
                },
                "duration_ms": 5000,
                "validation_errors": {},
                "status": "ok",
            }
        ],
    }

    r = client.post("/api/extension/learning/sync", json=payload)
    assert r.status_code == 202

    # Verify metric incremented
    final_count = learning_sync_counter.labels(status="stub")._value._value
    assert final_count > initial_count
