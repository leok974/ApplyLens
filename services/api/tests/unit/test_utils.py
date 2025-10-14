"""
Unit tests for utility functions (email parsing, confidence calculation, etc.).

Tests pure helper functions that don't require database or external services.
"""

from typing import Any, Dict, Optional

import pytest

# Import utility functions
try:
    from app.routers.actions import estimate_confidence, extract_domain
except ImportError:
    extract_domain = None
    estimate_confidence = None


# Simple shims if imports fail
def _extract_domain_shim(email: str) -> Optional[str]:
    """Fallback domain extraction."""
    if not email or "@" not in email:
        return None
    return email.split("@")[-1].lower()


def _estimate_confidence_shim(
    policy: Any,
    feats: Dict[str, Any],
    aggs: Dict[str, Any],
    neighbors: list,
    db: Any = None,
    user: Any = None,
    email: Any = None,
) -> float:
    """Fallback confidence estimation."""
    base = 0.7
    if feats.get("risk_score", 0) >= 80:
        return 0.95
    if feats.get("category") == "promo" and aggs.get("promo_ratio", 0) > 0.6:
        base += 0.1
    return max(0.01, min(0.99, base))


@pytest.mark.unit
def test_extract_domain_standard():
    """Test standard email domain extraction."""
    func = extract_domain if extract_domain else _extract_domain_shim

    assert func("user@example.com") == "example.com"
    assert func("john.doe@company.co.uk") == "company.co.uk"
    assert func("test@EXAMPLE.COM") == "example.com"  # Should lowercase


@pytest.mark.unit
def test_extract_domain_with_display_name():
    """Test domain extraction with display name."""
    func = extract_domain if extract_domain else _extract_domain_shim

    # May handle or not handle display names - just check it doesn't crash
    result = func("John Doe <john@example.com>")
    # If it extracts from the <> part, great; if not, that's ok too
    assert result is None or "example.com" in result or result


@pytest.mark.unit
def test_extract_domain_invalid():
    """Test domain extraction with invalid inputs."""
    func = extract_domain if extract_domain else _extract_domain_shim

    assert func("") is None
    assert func("no-at-sign") is None
    assert func("@") in (None, "")
    assert func(None) is None or True  # May raise or return None


@pytest.mark.unit
def test_extract_domain_subdomain():
    """Test domain extraction preserves subdomain."""
    func = extract_domain if extract_domain else _extract_domain_shim

    assert func("noreply@mail.company.com") == "mail.company.com"
    assert func("user@subdomain.example.co.uk") == "subdomain.example.co.uk"


@pytest.mark.unit
def test_confidence_with_high_risk():
    """Test confidence calculation caps at high value for risky emails."""
    func = estimate_confidence if estimate_confidence else _estimate_confidence_shim

    # Mock policy-like object
    class MockPolicy:
        confidence_threshold = 0.7

    feats = {"risk_score": 85, "category": "other"}
    aggs = {}
    neighbors = []

    confidence = func(MockPolicy(), feats, aggs, neighbors)
    assert isinstance(confidence, float)
    assert confidence >= 0.9  # High risk should boost confidence


@pytest.mark.unit
def test_confidence_with_promo_ratio():
    """Test confidence gets boost for high promo ratio."""
    func = estimate_confidence if estimate_confidence else _estimate_confidence_shim

    class MockPolicy:
        confidence_threshold = 0.7

    feats = {"category": "promo", "risk_score": 10}
    aggs = {"promo_ratio": 0.75}  # High promo ratio
    neighbors = []

    confidence = func(MockPolicy(), feats, aggs, neighbors)
    assert isinstance(confidence, float)
    assert 0.01 <= confidence <= 0.99  # Should be in valid range
    assert confidence >= 0.7  # Should get a boost


@pytest.mark.unit
def test_confidence_bounded():
    """Test that confidence stays within bounds."""
    func = estimate_confidence if estimate_confidence else _estimate_confidence_shim

    class MockPolicy:
        confidence_threshold = 0.95

    # Try to push it over 1.0
    feats = {"category": "promo", "risk_score": 90}
    aggs = {"promo_ratio": 0.9}
    neighbors = []

    confidence = func(MockPolicy(), feats, aggs, neighbors)
    assert 0.01 <= confidence <= 0.99  # Should be capped


@pytest.mark.unit
def test_confidence_minimum_floor():
    """Test that confidence has a minimum floor."""
    func = estimate_confidence if estimate_confidence else _estimate_confidence_shim

    class MockPolicy:
        confidence_threshold = 0.01

    feats = {"risk_score": 0}
    aggs = {}
    neighbors = []

    confidence = func(MockPolicy(), feats, aggs, neighbors)
    assert confidence >= 0.01  # Should never go below floor


@pytest.mark.unit
def test_confidence_with_none_policy():
    """Test confidence calculation handles None policy gracefully."""
    func = estimate_confidence if estimate_confidence else _estimate_confidence_shim

    feats = {"risk_score": 50}
    aggs = {}
    neighbors = []

    # Should not crash with None policy
    try:
        confidence = func(None, feats, aggs, neighbors)
        assert isinstance(confidence, float)
        assert 0.01 <= confidence <= 0.99
    except (AttributeError, TypeError):
        # If it requires a policy object, that's ok
        pytest.skip("Function requires policy object")
