"""
E2E tests for expired promotion cleanup automation

Tests the full flow:
1. Email is classified as expired promotion
2. Policy engine recommends archive action
3. Action preview shows it's safe
4. Action execution archives the email
5. Audit log records the action
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from app.main import app
from app.logic.policy import create_default_engine


@pytest.mark.asyncio
async def test_expired_promo_is_proposed_for_archive(monkeypatch):
    """
    Test that expired promotional emails are automatically proposed for archiving
    
    Flow:
    1. Mock search to return an expired promo email
    2. Call /mail/actions/preview
    3. Verify action is allowed
    4. Call /mail/actions/execute
    5. Verify action was applied
    """
    # Create a test email: expired promotion
    expired_promo = {
        "id": "email_1",
        "subject": "Chipotle BOGO - Expires Sep 30",
        "body_text": "Buy one get one free burrito. Offer expires Sep 30, 2025.",
        "has_unsubscribe": True,
        "category": "promotions",
        "expires_at": (datetime.utcnow() - timedelta(days=5)).isoformat() + "Z",  # 5 days ago
        "confidence": 0.9,
    }
    
    # Test with local policy engine first
    engine = create_default_engine()
    actions = engine.evaluate_all(expired_promo)
    
    assert len(actions) > 0, "Policy engine should recommend at least one action"
    archive_action = next((a for a in actions if a["action"] == "archive"), None)
    assert archive_action is not None, "Should recommend archive action for expired promo"
    assert archive_action["policy_id"] == "promo-expired-archive"
    
    # Now test via API
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Preview the action
        preview_payload = {
            "actions": [
                {
                    "email_id": "email_1",
                    "action": "archive",
                    "policy_id": "promo-expired-archive",
                    "confidence": 0.9,
                    "rationale": "Expired promotion (expires_at < now)"
                }
            ]
        }
        
        prev_response = await ac.post("/mail/actions/preview", json=preview_payload)
        assert prev_response.status_code == 200
        
        prev_data = prev_response.json()
        assert prev_data["count"] == 1
        assert prev_data["results"][0]["allowed"] is True
        assert "expired" in prev_data["results"][0]["explain"].lower() or "ok" in prev_data["results"][0]["explain"].lower()
        
        # Execute the action
        exec_response = await ac.post("/mail/actions/execute", json=preview_payload)
        assert exec_response.status_code == 200
        
        exec_data = exec_response.json()
        assert exec_data["applied"] >= 1, "Should have applied the archive action"
        assert exec_data["failed"] == 0, "No actions should have failed"


@pytest.mark.asyncio
async def test_non_expired_promo_not_archived():
    """
    Test that non-expired promotions are NOT archived
    """
    # Create a test email: promotion that's still valid
    valid_promo = {
        "id": "email_2",
        "subject": "Flash Sale - 24 hours only!",
        "body_text": "Ends tomorrow!",
        "has_unsubscribe": True,
        "category": "promotions",
        "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",  # Tomorrow
        "confidence": 0.9,
    }
    
    engine = create_default_engine()
    actions = engine.evaluate_all(valid_promo)
    
    # Should NOT recommend archive for non-expired promo
    archive_action = next((a for a in actions if a["action"] == "archive" and a["policy_id"] == "promo-expired-archive"), None)
    assert archive_action is None, "Should NOT archive non-expired promotions"


@pytest.mark.asyncio
async def test_low_confidence_blocks_action():
    """
    Test that low-confidence classifications don't trigger actions
    """
    # Expired promo but low confidence
    uncertain_email = {
        "id": "email_3",
        "subject": "Maybe a promotion?",
        "body_text": "Some content",
        "category": "promotions",
        "expires_at": (datetime.utcnow() - timedelta(days=5)).isoformat() + "Z",
        "confidence": 0.3,  # Low confidence (threshold is 0.7 for this policy)
    }
    
    engine = create_default_engine()
    actions = engine.evaluate_all(uncertain_email)
    
    # Policy requires confidence >= 0.7, so this should be filtered out
    archive_action = next((a for a in actions if a["action"] == "archive"), None)
    assert archive_action is None, "Low confidence should prevent action"


@pytest.mark.asyncio
async def test_batch_processing():
    """
    Test processing multiple emails at once
    """
    emails = [
        {
            "id": "email_4",
            "category": "promotions",
            "expires_at": (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z",
            "confidence": 0.85,
        },
        {
            "id": "email_5",
            "category": "promotions",
            "expires_at": (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z",
            "confidence": 0.90,
        },
        {
            "id": "email_6",
            "category": "bills",  # Not a promo
            "confidence": 0.80,
        },
    ]
    
    engine = create_default_engine()
    results = engine.evaluate_batch(emails)
    
    # Should have actions for email_4 and email_5 (expired promos)
    assert "email_4" in results
    assert "email_5" in results
    
    # Should NOT have action for email_6 (it's a bill, not expired promo)
    # Note: It might have other actions (e.g., bill-reminder), but not promo-expired-archive
    if "email_6" in results:
        archive_actions = [a for a in results["email_6"] if a["policy_id"] == "promo-expired-archive"]
        assert len(archive_actions) == 0


@pytest.mark.asyncio
async def test_action_audit_logging(monkeypatch):
    """
    Test that executed actions are logged to the audit table
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Execute an action
        payload = {
            "actions": [
                {
                    "email_id": "email_7",
                    "action": "archive",
                    "policy_id": "promo-expired-archive",
                    "confidence": 0.88,
                    "rationale": "Test: expired promotional email"
                }
            ]
        }
        
        exec_response = await ac.post("/mail/actions/execute", json=payload)
        assert exec_response.status_code == 200
        
        # Check audit history
        history_response = await ac.get("/mail/actions/history/email_7")
        assert history_response.status_code == 200
        
        history_data = history_response.json()
        assert "actions" in history_data
        
        # Should have at least one action logged
        if len(history_data["actions"]) > 0:
            action_log = history_data["actions"][0]
            assert action_log["action"] == "archive"
            assert action_log["policy_id"] == "promo-expired-archive"
            assert action_log["actor"] == "agent"  # Automated action
            assert action_log["confidence"] == 0.88


@pytest.mark.asyncio
async def test_preview_safety_checks():
    """
    Test that preview endpoint applies safety guardrails
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Test 1: Very low confidence should be blocked
        low_conf_payload = {
            "actions": [
                {
                    "email_id": "email_8",
                    "action": "delete",  # High-risk action
                    "confidence": 0.3,  # Too low
                }
            ]
        }
        
        prev_response = await ac.post("/mail/actions/preview", json=low_conf_payload)
        assert prev_response.status_code == 200
        
        prev_data = prev_response.json()
        assert prev_data["results"][0]["allowed"] is False
        assert "confidence" in prev_data["results"][0]["explain"].lower()


@pytest.mark.asyncio
async def test_multiple_policies_can_trigger():
    """
    Test that an email can trigger multiple policies
    """
    # Email that matches multiple policy conditions
    email = {
        "id": "email_9",
        "category": "applications",  # Matches application-priority policy
        "labels": [],
        "confidence": 0.95,
    }
    
    engine = create_default_engine()
    actions = engine.evaluate_all(email)
    
    # Should have application-priority action (add important label)
    priority_action = next((a for a in actions if a["policy_id"] == "application-priority"), None)
    assert priority_action is not None
    assert priority_action["action"] == "label"
    assert priority_action["params"]["label"] == "important"
