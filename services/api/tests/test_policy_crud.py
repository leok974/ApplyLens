"""
Test policy CRUD endpoints

Tests the GET and PUT /api/policy/security endpoints for security policies.
"""
from fastapi.testclient import TestClient


def test_get_policy_creates_defaults(client: TestClient):
    """
    GET /api/policy/security should create a policy with default values
    if none exists yet.
    """
    response = client.get("/api/policy/security")
    assert response.status_code == 200
    
    data = response.json()
    # Check that defaults are returned
    assert "autoQuarantineHighRisk" in data
    assert "autoArchiveExpiredPromos" in data
    assert "autoUnsubscribeInactive" in data
    
    # Default values should match what's in the model
    assert data["autoQuarantineHighRisk"] is True
    assert data["autoArchiveExpiredPromos"] is True
    assert data["autoUnsubscribeInactive"]["enabled"] is False
    assert data["autoUnsubscribeInactive"]["threshold"] == 10


def test_put_policy_roundtrip(client: TestClient):
    """
    Test full roundtrip: GET → modify → PUT → GET again
    Verify that updated values persist correctly.
    """
    # 1. Get initial policy
    r = client.get("/api/policy/security")
    assert r.status_code == 200
    base = r.json()
    
    # 2. Update with new values
    updated_policy = {
        "auto_quarantine_high_risk": not base["autoQuarantineHighRisk"],
        "auto_archive_expired_promos": not base["autoArchiveExpiredPromos"],
        "auto_unsubscribe_inactive": {
            "enabled": True,
            "threshold": 7
        }
    }
    
    r = client.put("/api/policy/security", json=updated_policy)
    assert r.status_code == 200
    got = r.json()
    
    # 3. Verify response matches what we sent
    assert got["autoQuarantineHighRisk"] == updated_policy["auto_quarantine_high_risk"]
    assert got["autoArchiveExpiredPromos"] == updated_policy["auto_archive_expired_promos"]
    assert got["autoUnsubscribeInactive"]["enabled"] is True
    assert got["autoUnsubscribeInactive"]["threshold"] == 7
    
    # 4. GET again to verify persistence
    r = client.get("/api/policy/security")
    assert r.status_code == 200
    persisted = r.json()
    
    assert persisted["autoQuarantineHighRisk"] == updated_policy["auto_quarantine_high_risk"]
    assert persisted["autoArchiveExpiredPromos"] == updated_policy["auto_archive_expired_promos"]
    assert persisted["autoUnsubscribeInactive"]["enabled"] is True
    assert persisted["autoUnsubscribeInactive"]["threshold"] == 7


def test_put_policy_partial_update(client: TestClient):
    """
    Test that PUT updates only the fields provided,
    preserving others that aren't included.
    """
    # Get current state
    r = client.get("/api/policy/security")
    assert r.status_code == 200
    base = r.json()
    
    # Update only auto_quarantine_high_risk
    partial_update = {
        "auto_quarantine_high_risk": not base["autoQuarantineHighRisk"],
        "auto_archive_expired_promos": base["autoArchiveExpiredPromos"],
        # Don't include auto_unsubscribe_inactive - should preserve existing
    }
    
    r = client.put("/api/policy/security", json=partial_update)
    assert r.status_code == 200
    got = r.json()
    
    # Verify the updated field changed
    assert got["autoQuarantineHighRisk"] == partial_update["auto_quarantine_high_risk"]
    # Verify other fields preserved
    assert got["autoArchiveExpiredPromos"] == base["autoArchiveExpiredPromos"]
    # Auto-unsubscribe should still have existing values
    assert got["autoUnsubscribeInactive"]["enabled"] == base["autoUnsubscribeInactive"]["enabled"]
    assert got["autoUnsubscribeInactive"]["threshold"] == base["autoUnsubscribeInactive"]["threshold"]


def test_put_policy_with_none_unsubscribe(client: TestClient):
    """
    Test that sending auto_unsubscribe_inactive as None/null
    defaults to enabled=False, threshold=10
    """
    update = {
        "auto_quarantine_high_risk": True,
        "auto_archive_expired_promos": True,
        "auto_unsubscribe_inactive": None  # Explicitly null
    }
    
    r = client.put("/api/policy/security", json=update)
    assert r.status_code == 200
    got = r.json()
    
    # Should default to disabled
    assert got["autoUnsubscribeInactive"]["enabled"] is False
    assert got["autoUnsubscribeInactive"]["threshold"] == 10
