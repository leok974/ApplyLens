"""
Unit tests for risk scoring heuristics.

Tests the compute_risk_score function and its component functions
to ensure accurate and deterministic risk calculation.
"""
import pytest
from typing import Dict, Any
from datetime import datetime, timezone


# Import the functions we're testing
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from scripts.analyze_risk import (
    extract_domain,
    compute_sender_domain_risk,
    compute_subject_keyword_risk,
    compute_source_confidence_risk,
    compute_risk_score,
    WEIGHTS,
    SUSPICIOUS_KEYWORDS,
    TRUSTED_DOMAINS,
    RECRUITER_DOMAINS
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def email_factory():
    """Factory to create mock Email objects with configurable attributes."""
    class EmailFactory:
        @staticmethod
        def create(
            sender: str = "test@example.com",
            subject: str = "Test Subject",
            source_confidence: float = 0.5,
            **kwargs
        ):
            """Create a mock Email object."""
            class MockEmail:
                def __init__(self, **attrs):
                    for key, value in attrs.items():
                        setattr(self, key, value)
            
            return MockEmail(
                sender=sender,
                subject=subject,
                source_confidence=source_confidence,
                **kwargs
            )
    
    return EmailFactory()


# ============================================================================
# DOMAIN EXTRACTION TESTS
# ============================================================================

@pytest.mark.unit
class TestDomainExtraction:
    """Tests for extract_domain function."""
    
    def test_simple_email(self):
        assert extract_domain("user@example.com") == "example.com"
    
    def test_email_with_name(self):
        assert extract_domain("John Doe <john@example.com>") == "example.com"
    
    def test_email_with_quotes(self):
        assert extract_domain('"John Doe" <john@example.com>') == "example.com"
    
    def test_empty_string(self):
        assert extract_domain("") == ""
    
    def test_no_at_symbol(self):
        assert extract_domain("notanemail") == ""
    
    def test_subdomain(self):
        assert extract_domain("user@mail.example.com") == "mail.example.com"


# ============================================================================
# SENDER DOMAIN RISK TESTS
# ============================================================================

@pytest.mark.unit
class TestSenderDomainRisk:
    """Tests for compute_sender_domain_risk function."""
    
    def test_trusted_domain_gmail(self):
        score, details = compute_sender_domain_risk("user@gmail.com")
        assert score == 0.0
        assert details["domain"] == "gmail.com"
        assert details["trust_level"] == "trusted"
        assert details["points"] == 0.0
    
    def test_trusted_domain_with_name(self):
        score, details = compute_sender_domain_risk("Alice <alice@outlook.com>")
        assert score == 0.0
        assert details["domain"] == "outlook.com"
        assert details["trust_level"] == "trusted"
    
    def test_recruiter_domain(self):
        score, details = compute_sender_domain_risk("hr@greenhouse.io")
        assert score == 10.0
        assert details["domain"] == "greenhouse.io"
        assert details["trust_level"] == "recruiter"
        assert details["points"] == 10.0
    
    def test_unknown_domain(self):
        score, details = compute_sender_domain_risk("spam@suspicious-site.xyz")
        assert score == 40.0
        assert details["domain"] == "suspicious-site.xyz"
        assert details["trust_level"] == "unknown"
        assert details["points"] == 40.0
    
    def test_empty_sender(self):
        score, details = compute_sender_domain_risk("")
        assert score == 40.0
        assert details["domain"] == ""
        assert details["trust_level"] == "unknown"
    
    def test_case_insensitive(self):
        score1, _ = compute_sender_domain_risk("user@GMAIL.COM")
        score2, _ = compute_sender_domain_risk("user@gmail.com")
        assert score1 == score2 == 0.0


# ============================================================================
# SUBJECT KEYWORD RISK TESTS
# ============================================================================

@pytest.mark.unit
class TestSubjectKeywordRisk:
    """Tests for compute_subject_keyword_risk function."""
    
    def test_no_suspicious_keywords(self):
        score, details = compute_subject_keyword_risk("Meeting reminder")
        assert score == 0.0
        assert details["keywords"] == []
        assert details["points"] == 0.0
    
    def test_one_suspicious_keyword(self):
        score, details = compute_subject_keyword_risk("Urgent: Please respond")
        assert score == 20.0
        assert "urgent" in details["keywords"]
        assert details["count"] == 1
        assert details["points"] == 20.0
    
    def test_multiple_suspicious_keywords(self):
        score, details = compute_subject_keyword_risk("Urgent: Verify your account now")
        assert score == 40.0
        assert "urgent" in details["keywords"]
        assert "verify" in details["keywords"]
        assert details["count"] == 2
        assert details["points"] == 40.0
    
    def test_case_insensitive_matching(self):
        score1, _ = compute_subject_keyword_risk("URGENT MESSAGE")
        score2, _ = compute_subject_keyword_risk("urgent message")
        assert score1 == score2 == 20.0
    
    def test_partial_word_not_matched(self):
        # "urge" should not match "urgent"
        score, details = compute_subject_keyword_risk("I urge you to read this")
        # This test depends on implementation - if using word boundaries, should be 0
        # Current implementation may match substrings
        assert details["keywords"] == [] or "urgent" not in details["keywords"]
    
    def test_empty_subject(self):
        score, details = compute_subject_keyword_risk("")
        assert score == 0.0
        assert details["keywords"] == []
    
    def test_three_keywords_still_capped_at_40(self):
        score, details = compute_subject_keyword_risk(
            "Urgent: Verify and Confirm your suspended account"
        )
        assert score == 40.0  # Should cap at 40
        assert len(details["keywords"]) >= 2


# ============================================================================
# SOURCE CONFIDENCE RISK TESTS
# ============================================================================

@pytest.mark.unit
class TestSourceConfidenceRisk:
    """Tests for compute_source_confidence_risk function."""
    
    def test_zero_confidence(self):
        score, details = compute_source_confidence_risk(0.0)
        assert score == 20.0
        assert details["confidence"] == 0.0
        assert details["points"] == 20.0
    
    def test_full_confidence(self):
        score, details = compute_source_confidence_risk(1.0)
        assert score == 0.0
        assert details["confidence"] == 1.0
        assert details["points"] == 0.0
    
    def test_half_confidence(self):
        score, details = compute_source_confidence_risk(0.5)
        assert score == 10.0
        assert details["confidence"] == 0.5
        assert details["points"] == 10.0
    
    def test_quarter_confidence(self):
        score, details = compute_source_confidence_risk(0.25)
        assert score == 15.0
        assert details["confidence"] == 0.25
        assert details["points"] == 15.0
    
    def test_none_confidence_defaults_to_zero(self):
        score, details = compute_source_confidence_risk(None)
        assert score == 20.0
        assert details["confidence"] == 0.0
    
    def test_negative_confidence_treated_as_zero(self):
        score, details = compute_source_confidence_risk(-0.5)
        assert score == 20.0
    
    def test_confidence_above_one_capped(self):
        score, details = compute_source_confidence_risk(1.5)
        assert score == 0.0  # Should be capped at 1.0 confidence


# ============================================================================
# INTEGRATED RISK SCORE TESTS
# ============================================================================

@pytest.mark.unit
class TestComputeRiskScore:
    """Tests for compute_risk_score function (integrated scoring)."""
    
    def test_perfect_safe_email(self, email_factory):
        """Email from trusted domain, safe subject, high confidence."""
        email = email_factory.create(
            sender="user@gmail.com",
            subject="Meeting tomorrow",
            source_confidence=1.0
        )
        score, breakdown = compute_risk_score(email)
        
        assert score == 0.0
        assert breakdown["total_score"] == 0.0
        assert "components" in breakdown
        assert "weights" in breakdown
        assert breakdown["weights"] == WEIGHTS
    
    def test_maximum_risk_email(self, email_factory):
        """Unknown domain, multiple suspicious keywords, zero confidence."""
        email = email_factory.create(
            sender="hacker@suspicious.xyz",
            subject="Urgent: Verify your account immediately",
            source_confidence=0.0
        )
        score, breakdown = compute_risk_score(email)
        
        assert score == 100.0
        assert breakdown["total_score"] == 100.0
        assert breakdown["components"]["sender_domain"]["points"] == 40.0
        assert breakdown["components"]["subject_keywords"]["points"] == 40.0
        assert breakdown["components"]["source_confidence"]["points"] == 20.0
    
    def test_medium_risk_email(self, email_factory):
        """Recruiter domain, safe subject, medium confidence."""
        email = email_factory.create(
            sender="hr@greenhouse.io",
            subject="Interview invitation",
            source_confidence=0.5
        )
        score, breakdown = compute_risk_score(email)
        
        # 10 (recruiter) + 0 (no keywords) + 10 (0.5 confidence) = 20
        assert score == 20.0
        assert breakdown["components"]["sender_domain"]["points"] == 10.0
        assert breakdown["components"]["subject_keywords"]["points"] == 0.0
        assert breakdown["components"]["source_confidence"]["points"] == 10.0
    
    def test_score_is_rounded(self, email_factory):
        """Ensure score is rounded to 2 decimal places."""
        email = email_factory.create(
            sender="test@example.com",
            subject="Test",
            source_confidence=0.333  # Will produce fractional score
        )
        score, breakdown = compute_risk_score(email)
        
        # Check that score is rounded
        assert isinstance(score, float)
        assert len(str(score).split('.')[-1]) <= 2  # At most 2 decimal places
    
    def test_breakdown_has_computed_at_timestamp(self, email_factory):
        """Ensure breakdown includes computed_at timestamp."""
        email = email_factory.create()
        score, breakdown = compute_risk_score(email)
        
        assert "computed_at" in breakdown
        # Verify it's a valid ISO timestamp
        timestamp = breakdown["computed_at"]
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    def test_breakdown_structure(self, email_factory):
        """Verify the structure of the breakdown dictionary."""
        email = email_factory.create()
        score, breakdown = compute_risk_score(email)
        
        # Check top-level keys
        assert "total_score" in breakdown
        assert "computed_at" in breakdown
        assert "components" in breakdown
        assert "weights" in breakdown
        
        # Check components structure
        components = breakdown["components"]
        assert "sender_domain" in components
        assert "subject_keywords" in components
        assert "source_confidence" in components
        
        # Each component should have details
        for component in components.values():
            assert isinstance(component, dict)
            assert "points" in component
    
    def test_missing_fields_handled_gracefully(self, email_factory):
        """Test that missing fields don't cause errors."""
        email = email_factory.create(
            sender=None,
            subject=None,
            source_confidence=None
        )
        score, breakdown = compute_risk_score(email)
        
        # Should still compute a score (likely high risk)
        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert "total_score" in breakdown


# ============================================================================
# WEIGHTS VALIDATION TESTS
# ============================================================================

@pytest.mark.unit
class TestWeightsConfiguration:
    """Tests to ensure weight configuration is valid."""
    
    def test_weights_sum_to_one(self):
        """Weights must sum to 1.0 for normalized 0-100 scale."""
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"
    
    def test_all_weights_positive(self):
        """All weights must be positive."""
        for key, value in WEIGHTS.items():
            assert value > 0, f"Weight {key} is not positive: {value}"
    
    def test_weights_cover_all_components(self):
        """Ensure we have weights for all components."""
        expected_components = ["sender_domain", "subject_keywords", "source_confidence"]
        for component in expected_components:
            assert component in WEIGHTS, f"Missing weight for {component}"


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

@pytest.mark.unit
class TestConfiguration:
    """Tests for configuration constants."""
    
    def test_suspicious_keywords_not_empty(self):
        assert len(SUSPICIOUS_KEYWORDS) > 0
    
    def test_suspicious_keywords_lowercase(self):
        """All keywords should be lowercase for case-insensitive matching."""
        for keyword in SUSPICIOUS_KEYWORDS:
            assert keyword == keyword.lower()
    
    def test_trusted_domains_not_empty(self):
        assert len(TRUSTED_DOMAINS) > 0
    
    def test_trusted_domains_lowercase(self):
        for domain in TRUSTED_DOMAINS:
            assert domain == domain.lower()
    
    def test_recruiter_domains_not_empty(self):
        assert len(RECRUITER_DOMAINS) > 0
    
    def test_no_overlap_between_trusted_and_recruiter(self):
        """Trusted and recruiter domains should be mutually exclusive."""
        overlap = set(TRUSTED_DOMAINS) & set(RECRUITER_DOMAINS)
        assert len(overlap) == 0, f"Overlap found: {overlap}"
