"""
Unit tests for risk heuristics.
"""

from app.logic.risk import (
    analyze_email_risk,
    looks_like_punycode,
    parse_from,
    risk_score,
    spoof_similarity,
    tld_risk,
)


def test_display_name_spoof():
    """Test detection of display name spoofing (brand impersonation)."""
    # "PayPal" in display but domain is NOT paypal.com
    # Using capital I instead of lowercase l to create lookalike
    hdr = "PayPal Billing <support@paypaI.com>"
    s = risk_score(hdr, ["https://paypaI.com/login"])

    # Spoof component alone is 60 points
    assert s >= 60, f"Expected score >= 60, got {s}"


def test_punycode_domain_adds_risk():
    """Test detection of punycode domains (IDN homograph attacks)."""
    # xn--pple-43d = аpple (cyrillic 'a')
    hdr = "Support <help@xn--pple-43d.com>"
    s = risk_score(hdr, ["https://xn--pple-43d.com/auth"])

    # Punycode domain is 30 points
    assert s >= 30, f"Expected score >= 30, got {s}"


def test_suspicious_tld():
    """Test detection of suspicious TLDs."""
    hdr = "Support <info@example.zip>"
    s = risk_score(hdr, [])

    # Suspicious TLD (.zip) adds 30 points
    assert s >= 9, f"Expected score >= 9 (30 * 0.3), got {s}"


def test_punycode_in_url():
    """Test detection of punycode in URLs."""
    hdr = "Legit Sender <info@example.com>"
    urls = [
        "https://xn--80akhbyknj4f.com/login",  # Russian chars
        "https://xn--e1afmkfd.com/verify",
    ]
    s = risk_score(hdr, urls)

    # Each punycode URL adds 10 points
    assert s >= 20, f"Expected score >= 20, got {s}"


def test_combined_risks():
    """Test that multiple risk factors stack."""
    # Spoof + punycode + suspicious TLD + punycode URL
    hdr = "PayPal Security <verify@paypal-secure.top>"
    urls = ["https://xn--paypal-verification.com/login"]
    s = risk_score(hdr, urls)

    # Spoof (60) + TLD risk (~9) + URL (10) = ~79
    assert s >= 70, f"Expected high score, got {s}"


def test_legitimate_email_low_risk():
    """Test that legitimate emails get low risk scores."""
    hdr = "John Doe <john@example.com>"
    s = risk_score(hdr, ["https://example.com/page"])

    assert s == 0, f"Expected score 0 for legit email, got {s}"


def test_parse_from_with_display_name():
    """Test parsing From header with display name."""
    hdr = '"PayPal Support" <noreply@paypal.com>'
    disp, dom = parse_from(hdr)

    assert disp == "PayPal Support"
    assert dom == "paypal.com"


def test_parse_from_without_display_name():
    """Test parsing From header without display name."""
    hdr = "support@example.com"
    disp, dom = parse_from(hdr)

    assert disp == ""
    assert dom == "example.com"


def test_parse_from_with_quotes():
    """Test parsing From header with various quote formats."""
    hdr = "PayPal Billing <billing@paypal.com>"
    disp, dom = parse_from(hdr)

    assert disp == "PayPal Billing"
    assert dom == "paypal.com"


def test_looks_like_punycode_positive():
    """Test punycode detection - positive cases."""
    assert looks_like_punycode("xn--pple-43d.com")
    assert looks_like_punycode("example.xn--80akhbyknj4f.com")
    assert looks_like_punycode("XN--TEST.COM")  # Case insensitive


def test_looks_like_punycode_negative():
    """Test punycode detection - negative cases."""
    assert not looks_like_punycode("apple.com")
    assert not looks_like_punycode("example.com")
    assert not looks_like_punycode("sub.domain.org")


def test_spoof_similarity_paypal():
    """Test spoof detection for PayPal brand."""
    # Brand in display, wrong domain
    score = spoof_similarity("PayPal Billing", "paypaI.com")
    assert score == 1.0

    # Brand in display, correct domain
    score = spoof_similarity("PayPal Billing", "paypal.com")
    assert score == 0.0


def test_spoof_similarity_microsoft():
    """Test spoof detection for Microsoft brand."""
    score = spoof_similarity("Microsoft Account Team", "micros0ft.com")
    assert score == 1.0

    score = spoof_similarity("Microsoft Account Team", "microsoft.com")
    assert score == 0.0


def test_spoof_similarity_no_brand():
    """Test that non-brand display names don't trigger spoof detection."""
    score = spoof_similarity("John Doe", "example.com")
    assert score == 0.0


def test_tld_risk_suspicious():
    """Test suspicious TLD detection."""
    assert tld_risk("example.zip") == 0.3
    assert tld_risk("phishing.tk") == 0.3
    assert tld_risk("scam.top") == 0.3


def test_tld_risk_normal():
    """Test normal TLD detection."""
    assert tld_risk("example.com") == 0.0
    assert tld_risk("company.org") == 0.0
    assert tld_risk("service.io") == 0.0


def test_analyze_email_risk_comprehensive():
    """Test comprehensive email risk analysis."""
    email_doc = {
        "from_addr": "PayPal Security <verify@paypal-check.top>",
        "urls": ["https://xn--paypal.com/verify", "https://example.com"],
    }

    result = analyze_email_risk(email_doc)

    assert result["risk_score"] >= 60
    assert "display_name_spoof" in result["risk_factors"]
    assert "suspicious_tld" in result["risk_factors"]
    assert "punycode_url" in result["risk_factors"]


def test_analyze_email_risk_legitimate():
    """Test risk analysis for legitimate email."""
    email_doc = {
        "from_addr": "John Doe <john@example.com>",
        "urls": ["https://example.com/page"],
    }

    result = analyze_email_risk(email_doc)

    assert result["risk_score"] == 0
    assert len(result["risk_factors"]) == 0


def test_risk_score_clamped_at_100():
    """Test that risk score is clamped to max 100."""
    # Create scenario with excessive risk
    hdr = "PayPal Microsoft Apple Amazon <fake@phishing.zip>"
    urls = ["https://xn--test" + str(i) + ".com" for i in range(20)]

    s = risk_score(hdr, urls)

    assert s <= 100, f"Score should be clamped at 100, got {s}"


def test_risk_score_at_minimum():
    """Test that risk score cannot go below 0."""
    hdr = "Legit <info@example.com>"
    s = risk_score(hdr, [])

    assert s >= 0, f"Score should be >= 0, got {s}"


def test_mailto_urls_ignored():
    """Test that mailto: URLs don't contribute to risk."""
    hdr = "Contact <info@example.com>"
    urls = ["mailto:support@example.com", "mailto:sales@example.com"]

    s = risk_score(hdr, urls)

    # Should ignore mailto links (@ in URL)
    assert s == 0
