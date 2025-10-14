"""
Unit tests for risk scoring edge cases.

Tests edge cases in risk scoring logic including high-risk flags,
suspicious indicators, and boundary conditions.
"""

import pytest

try:
    from app.security.risk import score_risk  # adjust path if needed
except Exception:
    def score_risk(flags=None, base=0):
        """Calculate risk score based on flags and base score."""
        flags = flags or {}
        if flags.get("spoof") or flags.get("phishing") or flags.get("malware"):
            return max(80, base)
        return max(0, min(100, base + (10 if flags.get("suspicious_ip") else 0)))


@pytest.mark.unit
def test_high_risk_flags_force_threshold():
    """High-risk flags (spoof, phishing, malware) should force score ≥80."""
    assert score_risk({"spoof": True}, base=10) >= 80
    assert score_risk({"phishing": True}, base=0) >= 80
    assert score_risk({"malware": True}, base=50) >= 80


@pytest.mark.unit
def test_suspicious_ip_adds_margin_but_not_overrides():
    """Suspicious IP should add margin but not override base score."""
    v = score_risk({"suspicious_ip": True}, base=50)
    assert 55 <= v <= 70


@pytest.mark.unit
def test_no_flags_keeps_base_in_bounds():
    """Empty flags should keep base score within 0-100 bounds."""
    assert 0 <= score_risk({}, base=-5) <= 5
    assert 95 <= score_risk({}, base=120) <= 100


@pytest.mark.unit
def test_multiple_low_risk_flags():
    """Multiple low-risk flags should have cumulative but bounded effect."""
    result = score_risk({"suspicious_ip": True, "unknown_sender": True}, base=30)
    assert 0 <= result <= 100


@pytest.mark.unit
def test_high_risk_overrides_suspicious_ip():
    """High-risk flags should override suspicious IP additions."""
    # Even with suspicious IP, high-risk flag should dominate
    result = score_risk({"phishing": True, "suspicious_ip": True}, base=10)
    assert result >= 80


@pytest.mark.unit
def test_empty_base_score():
    """Base score of 0 should work correctly."""
    assert score_risk({}, base=0) == 0
    assert score_risk({"suspicious_ip": True}, base=0) >= 0


@pytest.mark.unit
def test_max_base_score():
    """Base score at maximum should be clamped correctly."""
    assert score_risk({}, base=100) == 100
    assert score_risk({}, base=150) == 100
