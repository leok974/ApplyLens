"""Integration tests for /api/opportunities endpoint.

Tests the full endpoint behavior including filtering of job alerts,
newsletters, and closed applications.
"""

import pytest
from datetime import datetime, timezone

from app.models import Application, AppStatus, Email


@pytest.fixture
def test_user_email():
    """Test user email for authentication."""
    return "test@example.com"


@pytest.fixture
def auth_headers(test_user_email):
    """Headers for authenticated requests."""
    return {"X-User-Email": test_user_email}


@pytest.mark.asyncio
async def test_opportunities_excludes_job_alerts_and_newsletters(
    async_client, db_session, test_user_email, auth_headers
):
    """Test that /api/opportunities excludes noise but includes real opportunities."""

    # ===== Arrange: Create test data =====

    # 1) Real interview thread - SHOULD BE INCLUDED
    interview_email = Email(
        subject="Onsite interview - next steps",
        sender="recruiter@fancycompany.com",
        body_text="Hi, we'd like to schedule an onsite interview...",
        owner_email=test_user_email,
        received_at=datetime.now(timezone.utc),
        category="interview_invite",
        company="FancyCompany",
        role="ML Engineer",
        thread_id="thread-interview-123",
    )
    db_session.add(interview_email)
    db_session.flush()

    # Link to active application
    app_interview = Application(
        company="FancyCompany",
        role="ML Engineer",
        status=AppStatus.interview,
        thread_id="thread-interview-123",
    )
    db_session.add(app_interview)
    db_session.flush()

    # Link email to application
    interview_email.application_id = app_interview.id

    # 2) Job alert from Indeed - SHOULD BE EXCLUDED
    alert_email = Email(
        subject="New jobs for you - Backend Developer",
        sender="alerts@indeed.com",
        body_text="Check out these 5 new jobs matching your search.",
        owner_email=test_user_email,
        received_at=datetime.now(timezone.utc),
        category=None,
        thread_id="thread-alert-456",
    )
    db_session.add(alert_email)

    # 3) Newsletter/digest - SHOULD BE EXCLUDED
    newsletter_email = Email(
        subject="Weekly Tech Jobs Digest",
        sender="newsletter@techjobs.com",
        body_text="Here are this week's top tech jobs...",
        owner_email=test_user_email,
        received_at=datetime.now(timezone.utc),
        category="newsletter",
        thread_id="thread-newsletter-789",
    )
    db_session.add(newsletter_email)

    # 4) Rejected application - SHOULD BE EXCLUDED
    rejected_email = Email(
        subject="Application status update",
        sender="hr@rejectedcorp.com",
        body_text="Thank you for your interest. Unfortunately...",
        owner_email=test_user_email,
        received_at=datetime.now(timezone.utc),
        category="application_update",
        company="RejectedCorp",
        role="Senior Engineer",
        thread_id="thread-rejected-101",
    )
    db_session.add(rejected_email)
    db_session.flush()

    app_rejected = Application(
        company="RejectedCorp",
        role="Senior Engineer",
        status=AppStatus.rejected,
        thread_id="thread-rejected-101",
    )
    db_session.add(app_rejected)
    db_session.flush()

    rejected_email.application_id = app_rejected.id

    # 5) Recruiter outreach without application - SHOULD BE INCLUDED
    outreach_email = Email(
        subject="Exciting opportunity at StartupXYZ",
        sender="founder@startupxyz.com",
        body_text="Hi, I saw your profile and think you'd be perfect...",
        owner_email=test_user_email,
        received_at=datetime.now(timezone.utc),
        category="recruiter_outreach",
        company="StartupXYZ",
        role="Founding Engineer",
        thread_id="thread-outreach-202",
    )
    db_session.add(outreach_email)

    # 6) Job board mass mailing with bulk markers - SHOULD BE EXCLUDED
    bulk_email = Email(
        subject="Top jobs this week",
        sender="careers@ziprecruiter.com",
        body_text="View this email in your browser. Great jobs below. Click to unsubscribe.",
        owner_email=test_user_email,
        received_at=datetime.now(timezone.utc),
        category=None,
        thread_id="thread-bulk-303",
    )
    db_session.add(bulk_email)

    db_session.commit()

    # ===== Act: Call the endpoint =====
    resp = await async_client.get("/api/opportunities", headers=auth_headers)

    # ===== Assert: Check filtering worked =====
    assert resp.status_code == 200
    data = resp.json()

    # Should be a list
    assert isinstance(data, list)

    # Extract companies and roles from results
    companies = [item.get("company", "") for item in data]
    titles = [item.get("title", "") for item in data]

    # INCLUDED: Real interview thread
    assert "FancyCompany" in companies, "Interview thread should be included"
    assert any(
        "ML Engineer" in title for title in titles
    ), "ML Engineer role should be included"

    # INCLUDED: Recruiter outreach (even without application)
    assert "StartupXYZ" in companies, "Recruiter outreach should be included"
    assert any(
        "Founding Engineer" in title for title in titles
    ), "Founding Engineer role should be included"

    # EXCLUDED: Job alerts
    assert "Backend Developer" not in titles, "Indeed job alert should be excluded"

    # EXCLUDED: Newsletters
    assert not any(
        "Weekly" in (item.get("title") or "") for item in data
    ), "Newsletter should be excluded"

    # EXCLUDED: Rejected applications
    assert "RejectedCorp" not in companies, "Rejected application should be excluded"

    # EXCLUDED: Bulk mailings
    assert not any(
        "Top jobs" in (item.get("title") or "") for item in data
    ), "Bulk mailing should be excluded"

    # Overall count should be 2 (interview + outreach)
    assert len(data) == 2, f"Expected 2 opportunities, got {len(data)}"


@pytest.mark.asyncio
async def test_opportunities_filters_by_company(
    async_client, db_session, test_user_email, auth_headers
):
    """Test company filter works correctly."""

    # Create two opportunities with different companies
    email1 = Email(
        subject="Interview at Acme Corp",
        sender="hr@acme.com",
        body_text="We'd love to interview you",
        owner_email=test_user_email,
        received_at=datetime.now(timezone.utc),
        category="interview_invite",
        company="Acme Corp",
        role="Engineer",
        thread_id="thread-1",
    )
    db_session.add(email1)
    db_session.flush()

    app1 = Application(
        company="Acme Corp",
        role="Engineer",
        status=AppStatus.interview,
        thread_id="thread-1",
    )
    db_session.add(app1)
    db_session.flush()
    email1.application_id = app1.id

    email2 = Email(
        subject="Opportunity at TechStart",
        sender="founder@techstart.io",
        body_text="Interested in joining us?",
        owner_email=test_user_email,
        received_at=datetime.now(timezone.utc),
        category="recruiter_outreach",
        company="TechStart",
        role="Senior Dev",
        thread_id="thread-2",
    )
    db_session.add(email2)
    db_session.flush()

    app2 = Application(
        company="TechStart",
        role="Senior Dev",
        status=AppStatus.applied,
        thread_id="thread-2",
    )
    db_session.add(app2)
    db_session.flush()
    email2.application_id = app2.id

    db_session.commit()

    # Filter by "Acme"
    resp = await async_client.get(
        "/api/opportunities", params={"company": "Acme"}, headers=auth_headers
    )

    assert resp.status_code == 200
    data = resp.json()

    # Should only return Acme Corp
    assert len(data) == 1
    assert data[0]["company"] == "Acme Corp"


@pytest.mark.asyncio
async def test_opportunities_returns_empty_for_user_with_no_data(
    async_client, db_session, auth_headers
):
    """Test endpoint returns empty list when user has no opportunities."""

    # Don't create any emails for this user

    resp = await async_client.get("/api/opportunities", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_opportunities_pagination_works(
    async_client, db_session, test_user_email, auth_headers
):
    """Test limit and offset pagination parameters."""

    # Create 5 opportunities
    for i in range(5):
        email = Email(
            subject=f"Interview {i}",
            sender=f"hr{i}@company{i}.com",
            body_text="Interview opportunity",
            owner_email=test_user_email,
            received_at=datetime.now(timezone.utc),
            category="interview_invite",
            company=f"Company{i}",
            role=f"Role{i}",
            thread_id=f"thread-{i}",
        )
        db_session.add(email)
        db_session.flush()

        app = Application(
            company=f"Company{i}",
            role=f"Role{i}",
            status=AppStatus.interview,
            thread_id=f"thread-{i}",
        )
        db_session.add(app)
        db_session.flush()
        email.application_id = app.id

    db_session.commit()

    # Test limit
    resp = await async_client.get(
        "/api/opportunities", params={"limit": 2}, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    # Test offset
    resp = await async_client.get(
        "/api/opportunities", params={"limit": 2, "offset": 2}, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Should get different companies than first page
    first_page_companies = set()
    resp_first = await async_client.get(
        "/api/opportunities", params={"limit": 2, "offset": 0}, headers=auth_headers
    )
    for item in resp_first.json():
        first_page_companies.add(item["company"])

    second_page_companies = set(item["company"] for item in data)
    # Pages should not overlap
    assert len(first_page_companies & second_page_companies) == 0
