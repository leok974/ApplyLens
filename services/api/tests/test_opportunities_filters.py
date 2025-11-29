"""Unit tests for opportunity filtering logic.

Tests the helpers that detect job alerts, newsletters, and determine
whether an Email+Application pair represents a real opportunity.
"""

from unittest.mock import patch

from app.routers.opportunities import is_job_alert_or_blast, is_real_opportunity


class DummyEmail:
    """Mock Email object for testing."""

    def __init__(
        self,
        subject="",
        sender="",
        body_text="",
        category=None,
        labels=None,
    ):
        self.subject = subject
        self.sender = sender
        self.body_text = body_text
        self.category = category
        self.labels = labels or []


class DummyApp:
    """Mock Application object for testing."""

    def __init__(self, status):
        # Mock enum by creating an object with .value attribute
        class StatusEnum:
            def __init__(self, val):
                self.value = val

        self.status = StatusEnum(status) if status else None


# ===== Tests for is_job_alert_or_blast =====


def test_job_alert_detected_by_indeed_domain():
    """Job alerts from Indeed should be detected."""
    email = DummyEmail(
        subject="New jobs for you - React Developer in DC",
        sender="alerts@indeed.com",
        body_text="Click here to view more jobs.",
    )
    assert is_job_alert_or_blast(email) is True


def test_job_alert_detected_by_linkedin_domain():
    """Job alerts from LinkedIn should be detected."""
    email = DummyEmail(
        subject="Jobs you might be interested in",
        sender="noreply.linkedin.com",
        body_text="See recommended jobs based on your profile.",
    )
    assert is_job_alert_or_blast(email) is True


def test_job_alert_detected_by_subject_pattern():
    """Job alert subject patterns should be detected."""
    test_cases = [
        "New jobs for you - Backend Engineer",
        "Jobs you might like in San Francisco",
        "Job alerts: 5 new matches",
        "Top jobs this week",
        "Daily job digest - Frontend Developer",
        "Recommended jobs based on your search",
        "Job recommendations for Senior Engineer",
    ]

    for subject in test_cases:
        email = DummyEmail(
            subject=subject,
            sender="careers@company.com",
            body_text="Some job description here.",
        )
        assert is_job_alert_or_blast(email) is True, f"Failed to detect: {subject}"


def test_job_alert_detected_by_bulk_email_markers():
    """Bulk email markers (unsubscribe + browser view) should be detected."""
    email = DummyEmail(
        subject="Job opportunity",
        sender="recruiter@company.com",
        body_text="Great role here. View this email in your browser. Click to unsubscribe.",
    )
    assert is_job_alert_or_blast(email) is True


def test_real_recruiter_email_not_flagged_as_alert():
    """Real recruiter emails should NOT be flagged as job alerts."""
    email = DummyEmail(
        subject="Interview opportunity at TechCorp",
        sender="recruiter@techcorp.com",
        body_text="Hi there, I came across your profile and think you'd be a great fit...",
    )
    assert is_job_alert_or_blast(email) is False


def test_job_alert_unsubscribe_only_not_sufficient():
    """Just 'unsubscribe' without browser view shouldn't flag as bulk email."""
    email = DummyEmail(
        subject="Follow up on your application",
        sender="hr@company.com",
        body_text="Thanks for applying. If you don't want updates, unsubscribe here.",
    )
    assert is_job_alert_or_blast(email) is False


# ===== Tests for is_real_opportunity =====


def test_newsletter_filtered_by_helper():
    """Newsletters should be filtered out."""
    email = DummyEmail(
        subject="Weekly Tech Newsletter",
        sender="newsletter@techblog.com",
    )

    # Mock is_newsletter_or_digest to return True
    with patch("app.routers.opportunities.is_newsletter_or_digest", return_value=True):
        assert is_real_opportunity(email, None) is False


def test_job_alert_filtered_out():
    """Job board alerts should be filtered out."""
    email = DummyEmail(
        subject="New jobs for you - Data Scientist",
        sender="alerts@indeed.com",
        body_text="Check out these opportunities.",
    )

    with patch("app.routers.opportunities.is_newsletter_or_digest", return_value=False):
        assert is_real_opportunity(email, None) is False


def test_closed_application_excluded():
    """Applications with terminal status should be excluded."""
    email = DummyEmail(
        subject="Application status update",
        sender="hr@company.com",
    )
    app = DummyApp(status="rejected")

    with patch("app.routers.opportunities.is_newsletter_or_digest", return_value=False):
        assert is_real_opportunity(email, app) is False


def test_withdrawn_application_excluded():
    """Withdrawn applications should be excluded."""
    email = DummyEmail(
        subject="Re: Your application",
        sender="hr@company.com",
    )
    app = DummyApp(status="withdrawn")

    with patch("app.routers.opportunities.is_newsletter_or_digest", return_value=False):
        assert is_real_opportunity(email, app) is False


def test_live_interview_included():
    """Live interview threads should be included."""
    email = DummyEmail(
        subject="Interview confirmation - Senior Engineer",
        sender="recruiter@techcorp.com",
        category="interview_invite",
    )
    app = DummyApp(status="interview")

    with patch("app.routers.opportunities.is_newsletter_or_digest", return_value=False):
        assert is_real_opportunity(email, app) is True


def test_onsite_stage_included():
    """Onsite interview stage should be included."""
    email = DummyEmail(
        subject="Onsite interview details",
        sender="hr@company.com",
        category="onsite",
    )
    app = DummyApp(status="onsite")

    with patch("app.routers.opportunities.is_newsletter_or_digest", return_value=False):
        assert is_real_opportunity(email, app) is True


def test_offer_stage_included():
    """Offer stage should be included."""
    email = DummyEmail(
        subject="Offer letter - Software Engineer",
        sender="hr@company.com",
        category="offer",
    )
    app = DummyApp(status="offer")

    with patch("app.routers.opportunities.is_newsletter_or_digest", return_value=False):
        assert is_real_opportunity(email, app) is True


def test_unknown_category_excluded_when_present():
    """Emails with non-recruiting categories should be excluded."""
    email = DummyEmail(
        subject="Newsletter from recruiting firm",
        sender="info@recruitingfirm.com",
        category="newsletter",  # Explicitly non-recruiting category
    )
    app = DummyApp(status="interview")

    with patch("app.routers.opportunities.is_newsletter_or_digest", return_value=False):
        # Even with active application, non-recruiting category should exclude it
        assert is_real_opportunity(email, app) is False


def test_promo_category_excluded():
    """Promotional category emails should be excluded."""
    email = DummyEmail(
        subject="Special offer on our platform",
        sender="marketing@jobboard.com",
        category="promo",
    )
    app = None

    with patch("app.routers.opportunities.is_newsletter_or_digest", return_value=False):
        assert is_real_opportunity(email, app) is False


def test_no_category_with_active_application_included():
    """Email without category but with active application should be included."""
    email = DummyEmail(
        subject="Re: Your application",
        sender="hr@company.com",
        category=None,  # No category classification
    )
    app = DummyApp(status="applied")

    with patch("app.routers.opportunities.is_newsletter_or_digest", return_value=False):
        assert is_real_opportunity(email, app) is True


def test_recruiter_outreach_without_application_included():
    """Recruiter outreach emails should be included even without application."""
    email = DummyEmail(
        subject="Exciting opportunity at StartupXYZ",
        sender="recruiter@startupxyz.com",
        category="recruiter_outreach",
    )
    app = None

    with patch("app.routers.opportunities.is_newsletter_or_digest", return_value=False):
        assert is_real_opportunity(email, app) is True


def test_applications_category_included():
    """General 'applications' category should be included."""
    email = DummyEmail(
        subject="Your application to Company ABC",
        sender="careers@companyabc.com",
        category="applications",
    )
    app = DummyApp(status="applied")

    with patch("app.routers.opportunities.is_newsletter_or_digest", return_value=False):
        assert is_real_opportunity(email, app) is True


def test_invalid_application_status_excluded():
    """Applications with non-standard statuses should be excluded."""
    email = DummyEmail(
        subject="Application update",
        sender="hr@company.com",
    )
    # Status not in NEEDS_ATTENTION_STATUSES or CLOSED_STATUSES
    app = DummyApp(status="under_review")

    with patch("app.routers.opportunities.is_newsletter_or_digest", return_value=False):
        # Non-standard status should be excluded
        assert is_real_opportunity(email, app) is False
