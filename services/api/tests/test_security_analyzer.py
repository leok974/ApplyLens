# services/api/tests/test_security_analyzer.py
import os

from app.security.analyzer import (BlocklistProvider, EmailRiskAnalyzer,
                                   RiskAnalysis)

BL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app", "security", "blocklists.json"
)


def make_analyzer() -> EmailRiskAnalyzer:
    return EmailRiskAnalyzer(blocklists=BlocklistProvider(os.path.abspath(BL_PATH)))


def test_dmarc_fail_and_suspicious_tld_quarantines():
    """Test that DMARC fail + suspicious TLD results in quarantine"""
    az = make_analyzer()
    res: RiskAnalysis = az.analyze(
        headers={"Authentication-Results": "spf=fail dmarc=fail dkim=pass"},
        from_name="PayPal Support",
        from_email="notice@update-security-login.ru",
        subject="Urgent Action Required",
        body_text="please click the payment verification link",
        body_html=None,
        attachments=[],
        urls_visible_text_pairs=[("paypal.com", "http://update-security-login.ru/pay")],
        domain_first_seen_days_ago=0,
    )
    assert res.risk_score >= az.weights.QUARANTINE_THRESHOLD
    assert res.quarantined is True
    sigs = {f.signal for f in res.flags}
    assert "DMARC_FAIL" in sigs
    assert "SUSPICIOUS_TLD" in sigs
    assert "URL_HOST_MISMATCH" in sigs


def test_trusted_domain_reduces_risk():
    """Test that trusted domains get negative risk weight"""
    az = make_analyzer()
    res = az.analyze(
        headers={"Authentication-Results": "spf=pass dmarc=pass dkim=pass"},
        from_name="Google Security",
        from_email="no-reply@google.com",
        subject="Security alert",
        body_text="We detected a sign-in attempt",
        body_html="<p>Manage your account at https://accounts.google.com</p>",
        attachments=[],
        urls_visible_text_pairs=[],
        domain_first_seen_days_ago=365,
    )
    assert res.risk_score <= 10
    assert res.quarantined is False
    sigs = {f.signal for f in res.flags}
    assert "TRUSTED_DOMAIN" in sigs


def test_attachment_and_blocklisted_host():
    """Test that executable attachments and blocklisted hosts trigger quarantine"""
    az = make_analyzer()
    res = az.analyze(
        headers={},
        from_name="Billing",
        from_email="notify@billing-check.top",
        subject="Invoice",
        body_text="download invoice.exe",
        body_html=None,
        attachments=[
            {
                "filename": "invoice.exe",
                "mime_type": "application/octet-stream",
                "sha256": "",
            }
        ],
        urls_visible_text_pairs=[("download", "http://billing-check.top/i.exe")],
        domain_first_seen_days_ago=1,
    )
    sigs = {f.signal for f in res.flags}
    assert "EXECUTABLE_OR_HTML_ATTACHMENT" in sigs
    assert "BLOCKLISTED_HASH_OR_HOST" in sigs
    assert res.quarantined is True


def test_display_name_spoof():
    """Test that brand name mismatch is detected"""
    az = make_analyzer()
    res = az.analyze(
        headers={},
        from_name="PayPal Security Team",
        from_email="support@totally-not-paypal.com",
        subject="Verify your account",
        body_text="Please verify your PayPal account",
        body_html=None,
        attachments=[],
        urls_visible_text_pairs=[],
        domain_first_seen_days_ago=None,
    )
    sigs = {f.signal for f in res.flags}
    assert "DISPLAY_NAME_SPOOF" in sigs


def test_malicious_keywords():
    """Test that malicious keyword patterns are detected"""
    az = make_analyzer()
    res = az.analyze(
        headers={},
        from_name="Admin",
        from_email="admin@example.com",
        subject="Urgent action required",
        body_text="Please download the attached invoice.exe for payment verification link",
        body_html=None,
        attachments=[],
        urls_visible_text_pairs=[],
        domain_first_seen_days_ago=None,
    )
    sigs = {f.signal for f in res.flags}
    assert "MALICIOUS_KEYWORD" in sigs


def test_new_domain():
    """Test that newly registered domains are flagged"""
    az = make_analyzer()
    res = az.analyze(
        headers={},
        from_name="Support",
        from_email="help@brand-new-domain.com",
        subject="Welcome",
        body_text="Thanks for signing up",
        body_html=None,
        attachments=[],
        urls_visible_text_pairs=[],
        domain_first_seen_days_ago=1,
    )
    sigs = {f.signal for f in res.flags}
    assert "NEW_DOMAIN" in sigs


def test_spf_and_dkim_fail():
    """Test SPF and DKIM failures are detected"""
    az = make_analyzer()
    res = az.analyze(
        headers={"Authentication-Results": "spf=fail dkim=fail"},
        from_name="IT Department",
        from_email="it@company.com",
        subject="System update",
        body_text="Please install the attached update",
        body_html=None,
        attachments=[],
        urls_visible_text_pairs=[],
        domain_first_seen_days_ago=None,
    )
    sigs = {f.signal for f in res.flags}
    assert "SPF_FAIL" in sigs
    assert "DKIM_FAIL" in sigs


def test_html_attachment_flagged():
    """Test that HTML attachments are flagged as risky"""
    az = make_analyzer()
    res = az.analyze(
        headers={},
        from_name="Support",
        from_email="support@example.com",
        subject="Document",
        body_text="Please review the attached document",
        body_html=None,
        attachments=[
            {"filename": "document.html", "mime_type": "text/html", "sha256": ""}
        ],
        urls_visible_text_pairs=[],
        domain_first_seen_days_ago=None,
    )
    sigs = {f.signal for f in res.flags}
    assert "EXECUTABLE_OR_HTML_ATTACHMENT" in sigs


def test_clean_email_low_score():
    """Test that a clean email from trusted domain has low risk score"""
    az = make_analyzer()
    res = az.analyze(
        headers={"Authentication-Results": "spf=pass dmarc=pass dkim=pass"},
        from_name="GitHub",
        from_email="noreply@github.com",
        subject="New pull request",
        body_text="You have a new pull request on your repository",
        body_html="<p>View PR at https://github.com/user/repo/pull/123</p>",
        attachments=[],
        urls_visible_text_pairs=[],
        domain_first_seen_days_ago=3650,
    )
    assert res.risk_score < 20
    assert res.quarantined is False


def test_punycode_domain():
    """Test that punycode domains are flagged"""
    az = make_analyzer()
    res = az.analyze(
        headers={},
        from_name="Support",
        from_email="info@xn--exmple-cua.com",  # punycode domain
        subject="Important",
        body_text="Please review",
        body_html=None,
        attachments=[],
        urls_visible_text_pairs=[],
        domain_first_seen_days_ago=None,
    )
    sigs = {f.signal for f in res.flags}
    assert "PUNYCODE_OR_HOMOGLYPH" in sigs


def test_blocklisted_file_hash():
    """Test that blocklisted file hashes trigger high risk"""
    az = make_analyzer()
    res = az.analyze(
        headers={},
        from_name="Admin",
        from_email="admin@example.com",
        subject="Update",
        body_text="Install this update",
        body_html=None,
        attachments=[
            {
                "filename": "update.exe",
                "mime_type": "application/x-msdownload",
                "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            }
        ],
        urls_visible_text_pairs=[],
        domain_first_seen_days_ago=None,
    )
    sigs = {f.signal for f in res.flags}
    assert "BLOCKLISTED_HASH_OR_HOST" in sigs
    assert "EXECUTABLE_OR_HTML_ATTACHMENT" in sigs


def test_url_extraction_from_body():
    """Test that URLs are extracted from body text when not explicitly provided"""
    az = make_analyzer()
    res = az.analyze(
        headers={},
        from_name="Marketing",
        from_email="news@update-security-login.ru",
        subject="Special offer",
        body_text="Visit http://update-security-login.ru/offer for details",
        body_html="<a href='http://update-security-login.ru/offer'>Click here</a>",
        attachments=[],
        urls_visible_text_pairs=None,  # URLs should be extracted automatically
        domain_first_seen_days_ago=None,
    )
    sigs = {f.signal for f in res.flags}
    assert "BLOCKLISTED_HASH_OR_HOST" in sigs  # URL host is in blocklist
