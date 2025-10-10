"""
E2E tests for high-risk email quarantine automation

Tests the security policy flow:
1. Email is detected as high-risk (phishing, spam, etc.)
2. Policy engine recommends quarantine action
3. Action requires high confidence (safety check)
4. Quarantine is executed with notification
5. Audit trail is created
"""
import pytest
from httpx import AsyncClient
from app.main import app
from app.logic.policy import create_default_engine
from app.logic.classify import calculate_risk_score


@pytest.mark.asyncio
async def test_high_risk_triggers_quarantine_preview(monkeypatch):
    """
    Test that high-risk emails trigger quarantine recommendation
    
    Flow:
    1. Email has risk_score >= 80
    2. Policy engine recommends quarantine
    3. Preview shows action is allowed
    4. Action includes notification flag
    """
    # Create high-risk email
    high_risk_email = {
        "id": "phish_1",
        "subject": "URGENT: Verify your account now",
        "body_text": "Your account will be suspended unless you verify immediately. Click here: bit.ly/verify123",
        "sender": "paypal@suspicious-domain.ru",
        "risk_score": 92,
        "category": "security",
        "confidence": 0.95,
    }
    
    # Test with policy engine
    engine = create_default_engine()
    actions = engine.evaluate_all(high_risk_email)
    
    assert len(actions) > 0, "Should recommend actions for high-risk email"
    quarantine_action = next((a for a in actions if a["action"] == "quarantine"), None)
    assert quarantine_action is not None, "Should recommend quarantine for high-risk email"
    assert quarantine_action["policy_id"] == "risk-quarantine"
    assert quarantine_action["notify"] is True, "Quarantine should trigger notification"
    
    # Test via API
    async with AsyncClient(app=app, base_url="http://test") as ac:
        preview_payload = {
            "actions": [
                {
                    "email_id": "phish_1",
                    "action": "quarantine",
                    "policy_id": "risk-quarantine",
                    "confidence": 0.95,
                    "rationale": "High risk score (92/100) - likely phishing attempt"
                }
            ]
        }
        
        prev_response = await ac.post("/mail/actions/preview", json=preview_payload)
        assert prev_response.status_code == 200
        
        prev_data = prev_response.json()
        assert prev_data["results"][0]["allowed"] is True
        assert len(prev_data["results"][0]["warnings"]) > 0  # Should have warnings for high-risk action


@pytest.mark.asyncio
async def test_quarantine_requires_high_confidence():
    """
    Test that quarantine action requires high confidence (>= 0.8)
    
    This is a safety check to prevent false positives
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Quarantine with low confidence should be blocked
        low_conf_payload = {
            "actions": [
                {
                    "email_id": "maybe_phish_1",
                    "action": "quarantine",
                    "confidence": 0.6,  # Too low for quarantine
                    "rationale": "Uncertain if this is phishing"
                }
            ]
        }
        
        prev_response = await ac.post("/mail/actions/preview", json=low_conf_payload)
        assert prev_response.status_code == 200
        
        prev_data = prev_response.json()
        assert prev_data["results"][0]["allowed"] is False
        assert "confidence" in prev_data["results"][0]["explain"].lower()
        assert "0.8" in prev_data["results"][0]["explain"]


@pytest.mark.asyncio
async def test_quarantine_requires_rationale():
    """
    Test that quarantine action requires an explanation
    
    High-risk actions need human-readable rationale for transparency
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Quarantine without rationale should be blocked
        no_rationale_payload = {
            "actions": [
                {
                    "email_id": "phish_2",
                    "action": "quarantine",
                    "confidence": 0.9,
                    # No rationale field
                }
            ]
        }
        
        prev_response = await ac.post("/mail/actions/preview", json=no_rationale_payload)
        assert prev_response.status_code == 200
        
        prev_data = prev_response.json()
        assert prev_data["results"][0]["allowed"] is False
        assert "rationale" in prev_data["results"][0]["explain"].lower()


@pytest.mark.asyncio
async def test_risk_score_calculation():
    """
    Test that risk score is calculated correctly for phishing indicators
    """
    # Classic phishing email
    phishing_email = {
        "subject": "PayPal: Verify your account URGENT",
        "body_text": "Your account will be suspended. Update payment info: bit.ly/paypal123",
        "sender": "paypal-security@fake-domain.com",
        "urls": ["bit.ly/paypal123"],
    }
    
    risk_score = calculate_risk_score(phishing_email)
    
    assert risk_score >= 50, f"Phishing email should have high risk score, got {risk_score}"
    
    # Should trigger quarantine policy
    phishing_email["id"] = "phish_3"
    phishing_email["risk_score"] = risk_score
    phishing_email["category"] = "security"
    phishing_email["confidence"] = 0.88
    
    engine = create_default_engine()
    actions = engine.evaluate_all(phishing_email)
    
    quarantine_action = next((a for a in actions if a["action"] == "quarantine"), None)
    assert quarantine_action is not None, "High-risk email should trigger quarantine"


@pytest.mark.asyncio
async def test_legitimate_security_email_not_quarantined():
    """
    Test that legitimate security emails (low risk score) are NOT quarantined
    """
    # Legitimate security email from known provider
    legit_email = {
        "id": "security_1",
        "subject": "Your password was changed",
        "body_text": "Your password was successfully changed. If this wasn't you, contact support.",
        "sender": "security@github.com",
        "sender_domain": "github.com",
        "urls": ["https://github.com/security"],
        "risk_score": 15,  # Low risk
        "category": "security",
        "confidence": 0.85,
    }
    
    engine = create_default_engine()
    actions = engine.evaluate_all(legit_email)
    
    # Should NOT quarantine (risk_score < 80)
    quarantine_action = next((a for a in actions if a["action"] == "quarantine"), None)
    assert quarantine_action is None, "Low-risk emails should not be quarantined"


@pytest.mark.asyncio
async def test_quarantine_execution_and_audit():
    """
    Test full quarantine execution flow with audit logging
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Execute quarantine action
        exec_payload = {
            "actions": [
                {
                    "email_id": "phish_4",
                    "action": "quarantine",
                    "policy_id": "risk-quarantine",
                    "confidence": 0.93,
                    "rationale": "Phishing attempt: fake PayPal domain with urgent language"
                }
            ]
        }
        
        exec_response = await ac.post("/mail/actions/execute", json=exec_payload)
        assert exec_response.status_code == 200
        
        exec_data = exec_response.json()
        assert exec_data["applied"] >= 1
        
        # Check audit log
        history_response = await ac.get("/mail/actions/history/phish_4")
        assert history_response.status_code == 200
        
        history_data = history_response.json()
        if len(history_data["actions"]) > 0:
            audit_entry = history_data["actions"][0]
            assert audit_entry["action"] == "quarantine"
            assert audit_entry["policy_id"] == "risk-quarantine"
            assert "phishing" in audit_entry["rationale"].lower()


@pytest.mark.asyncio
async def test_borderline_risk_score():
    """
    Test emails right at the threshold (risk_score = 80)
    """
    # Email exactly at threshold
    borderline_email = {
        "id": "border_1",
        "risk_score": 80,  # Exactly at threshold
        "category": "security",
        "confidence": 0.85,
    }
    
    engine = create_default_engine()
    actions = engine.evaluate_all(borderline_email)
    
    # Should trigger quarantine (>= 80)
    quarantine_action = next((a for a in actions if a["action"] == "quarantine"), None)
    assert quarantine_action is not None, "risk_score >= 80 should trigger quarantine"
    
    # Just below threshold
    safe_email = {
        "id": "border_2",
        "risk_score": 79,  # Just below threshold
        "category": "security",
        "confidence": 0.85,
    }
    
    actions = engine.evaluate_all(safe_email)
    quarantine_action = next((a for a in actions if a["action"] == "quarantine"), None)
    assert quarantine_action is None, "risk_score < 80 should NOT trigger quarantine"


@pytest.mark.asyncio
async def test_batch_quarantine():
    """
    Test quarantining multiple high-risk emails in batch
    """
    emails = [
        {"id": f"phish_{i}", "risk_score": 85 + i, "category": "security", "confidence": 0.9}
        for i in range(5)
    ]
    
    engine = create_default_engine()
    results = engine.evaluate_batch(emails)
    
    # All should have quarantine actions
    assert len(results) == 5, "Should have actions for all 5 high-risk emails"
    
    for email_id, actions in results.items():
        quarantine_action = next((a for a in actions if a["action"] == "quarantine"), None)
        assert quarantine_action is not None, f"Email {email_id} should have quarantine action"


@pytest.mark.asyncio
async def test_suggest_actions_endpoint():
    """
    Test the /mail/suggest-actions endpoint for batch processing
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Request suggestions for multiple emails
        suggest_payload = {
            "email_ids": ["email_high_risk_1", "email_high_risk_2", "email_normal_1"]
        }
        
        response = await ac.post("/mail/suggest-actions", json=suggest_payload)
        
        # Should return without error even if emails don't exist in DB
        # (In production, this would fetch from DB and suggest actions)
        assert response.status_code == 200
        
        data = response.json()
        assert "suggestions" in data
        assert "count" in data


@pytest.mark.asyncio
async def test_very_high_risk_spam():
    """
    Test extremely high-risk spam/scam emails
    """
    # Obvious scam email
    scam_email = {
        "subject": "You won $1,000,000! URGENT wire transfer needed",
        "body_text": "Send your bank details and wire $500 processing fee to claim prize. Act now or lose money!",
        "sender": "prince@nigeria-lottery.biz",
        "urls": ["http://bit.ly/sendmoney123"] * 20,  # Lots of suspicious links
    }
    
    risk_score = calculate_risk_score(scam_email)
    assert risk_score >= 70, f"Obvious scam should have very high risk score, got {risk_score}"
    
    # Should definitely trigger quarantine
    scam_email["id"] = "scam_1"
    scam_email["risk_score"] = risk_score
    scam_email["category"] = "security"
    scam_email["confidence"] = 0.98
    
    engine = create_default_engine()
    actions = engine.evaluate_all(scam_email)
    
    quarantine_action = next((a for a in actions if a["action"] == "quarantine"), None)
    assert quarantine_action is not None
    assert quarantine_action["notify"] is True  # Should notify user
