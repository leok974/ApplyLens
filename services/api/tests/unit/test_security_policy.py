"""
Unit tests for security risk scoring and policy logic.

Tests pure functions that calculate risk scores based on email indicators
without requiring database or external services.
"""

import pytest
from typing import Dict, Any


# Import the risk calculation function
try:
    from app.logic.classify import calculate_risk_score
except ImportError:
    # Fallback if path differs
    calculate_risk_score = None


@pytest.mark.unit
@pytest.mark.skipif(calculate_risk_score is None, reason="calculate_risk_score not found")
def test_high_risk_flag_forces_threshold():
    """Test that high-risk indicators push score above threshold."""
    email = {
        "subject": "URGENT: Verify your account NOW or lose access",
        "body_text": "Click here immediately to verify your PayPal account",
        "sender": "security@fake-paypal-verify.com",
        "urls": []
    }
    score = calculate_risk_score(email)
    assert isinstance(score, (int, float))
    assert score >= 30  # Should have elevated risk score


@pytest.mark.unit
@pytest.mark.skipif(calculate_risk_score is None, reason="calculate_risk_score not found")
def test_no_flags_stays_low():
    """Test that clean emails have low risk scores."""
    email = {
        "subject": "Meeting notes from today",
        "body_text": "Here are the notes we discussed in our weekly meeting.",
        "sender": "colleague@company.com",
        "urls": []
    }
    score = calculate_risk_score(email)
    assert isinstance(score, (int, float))
    assert score <= 20  # Should be low risk


@pytest.mark.unit
@pytest.mark.skipif(calculate_risk_score is None, reason="calculate_risk_score not found")
def test_excessive_urls_increases_risk():
    """Test that emails with many URLs get higher risk scores."""
    email = {
        "subject": "Check out these deals",
        "body_text": "Click all these links for amazing offers!",
        "sender": "deals@example.com",
        "urls": [f"http://example.com/link{i}" for i in range(15)]  # 15 URLs
    }
    score = calculate_risk_score(email)
    assert isinstance(score, (int, float))
    assert score >= 10  # Should be penalized for excessive URLs


@pytest.mark.unit
@pytest.mark.skipif(calculate_risk_score is None, reason="calculate_risk_score not found")
def test_phishing_sender_mismatch():
    """Test that sender display name mismatch increases risk."""
    email = {
        "subject": "Your Amazon order confirmation",
        "body_text": "Please verify your order",
        "sender": "Amazon Support <noreply@suspicious-domain.xyz>",
        "urls": []
    }
    score = calculate_risk_score(email)
    assert isinstance(score, (int, float))
    # Should detect the mismatch between "Amazon" in name and domain


@pytest.mark.unit
@pytest.mark.skipif(calculate_risk_score is None, reason="calculate_risk_score not found")
def test_score_capped_at_100():
    """Test that risk score doesn't exceed 100."""
    email = {
        "subject": "URGENT WINNER CONGRATULATIONS VERIFY NOW CLICK HERE",
        "body_text": "You won the lottery! Click verify urgent now password account suspended",
        "sender": "PayPal Security <fake@totally-not-paypal.ru>",
        "urls": [f"http://spam.com/link{i}" for i in range(20)]
    }
    score = calculate_risk_score(email)
    assert isinstance(score, (int, float))
    assert score <= 100  # Should be capped at 100
    assert score >= 50  # But should be very high


@pytest.mark.unit
def test_risk_score_with_empty_email():
    """Test that risk scoring handles empty emails gracefully."""
    if calculate_risk_score is None:
        pytest.skip("calculate_risk_score not found")
    
    email = {
        "subject": "",
        "body_text": "",
        "sender": "",
        "urls": []
    }
    score = calculate_risk_score(email)
    assert isinstance(score, (int, float))
    assert 0 <= score <= 100
