# tests/test_applications.py
from app.db import SessionLocal
from app.gmail_service import upsert_application_for_email
from app.models import Application, AppStatus, Email


def test_upsert_application_from_email():
    """Test creating an application from an email with extracted metadata"""
    db = SessionLocal()
    try:
        # Clean up any existing test data (handle foreign key constraints)
        # First, clear last_email_id for ALL applications that reference test emails
        test_email_ids = (
            db.query(Email.id)
            .filter(
                Email.gmail_id.in_(
                    ["test_gmail_id_1", "test_gmail_id_2", "test_gmail_id_3"]
                )
            )
            .all()
        )
        test_email_ids = [e[0] for e in test_email_ids]
        if test_email_ids:
            db.query(Application).filter(
                Application.last_email_id.in_(test_email_ids)
            ).update({Application.last_email_id: None}, synchronize_session=False)
            db.flush()

        # Now delete test applications and emails
        db.query(Application).filter(
            Application.gmail_thread_id.in_(
                ["test_thread_A", "test_thread_B", "test_newsletter"]
            )
        ).delete(synchronize_session=False)
        db.query(Email).filter(
            Email.gmail_id.in_(
                ["test_gmail_id_1", "test_gmail_id_2", "test_gmail_id_3"]
            )
        ).delete(synchronize_session=False)
        db.commit()

        # Create a test email with extracted metadata
        e = Email(
            gmail_id="test_gmail_id_1",
            thread_id="test_thread_A",
            subject="Interview for AI Engineer",
            body_text="We'd like to schedule an interview with you for the AI Engineer position.",
            sender="hr@acme.com",
            recipient="me@example.com",
            company="Acme",
            role="AI Engineer",
            source="lever",
            source_confidence=0.9,
            label_heuristics=["interview"],
        )
        db.add(e)
        db.flush()

        # Upsert application from email
        app = upsert_application_for_email(db, e)
        db.commit()

        # Assertions
        assert app is not None
        assert app.company == "Acme"
        assert app.role == "AI Engineer"
        assert app.source == "lever"
        assert app.source_confidence == 0.9
        assert (
            app.status == AppStatus.interview
        )  # Should be interview due to label_heuristics
        assert app.thread_id == "test_thread_A"
        assert e.application_id == app.id

        print(
            f"✅ Test passed: Application {app.id} created and linked to email {e.id}"
        )

    finally:
        # Cleanup
        db.rollback()
        db.close()


def test_upsert_application_by_thread_id():
    """Test that emails with same thread_id link to same application"""
    db = SessionLocal()
    try:
        # Create first email
        e1 = Email(
            gmail_id="test_gmail_id_2",
            thread_id="test_thread_B",
            subject="Application confirmation",
            body_text="Thank you for applying",
            sender="jobs@example.com",
            recipient="me@example.com",
            company="Example Inc",
            role="Software Engineer",
            source="greenhouse",
            source_confidence=0.9,
        )
        db.add(e1)
        db.flush()

        app1 = upsert_application_for_email(db, e1)
        db.commit()

        # Create second email in same thread
        e2 = Email(
            gmail_id="test_gmail_id_3",
            thread_id="test_thread_B",
            subject="Re: Application confirmation",
            body_text="Interview scheduled",
            sender="jobs@example.com",
            recipient="me@example.com",
            company="Example Inc",
            role="Software Engineer",
            source="greenhouse",
            source_confidence=0.9,
            label_heuristics=["interview"],
        )
        db.add(e2)
        db.flush()

        app2 = upsert_application_for_email(db, e2)
        db.commit()

        # Should link to same application
        assert app1.id == app2.id
        assert e1.application_id == e2.application_id

        print(f"✅ Test passed: Both emails linked to same application {app1.id}")

    finally:
        db.rollback()
        db.close()


def test_no_application_without_metadata():
    """Test that emails without company/role/thread don't create applications"""
    db = SessionLocal()
    try:
        e = Email(
            gmail_id="test_gmail_id_4",
            subject="Newsletter",
            body_text="Check out our latest jobs",
            sender="newsletter@jobs.com",
            recipient="me@example.com",
        )
        db.add(e)
        db.flush()

        app = upsert_application_for_email(db, e)

        # Should return None
        assert app is None
        assert e.application_id is None

        print("✅ Test passed: No application created for newsletter email")

    finally:
        db.rollback()
        db.close()


def test_from_email_endpoint_autofill():
    """Test /from-email endpoint with automatic company/role extraction"""
    from fastapi.testclient import TestClient

    from app.db import SessionLocal
    from app.main import app

    client = TestClient(app)
    db = SessionLocal()

    try:
        # Clean up any existing test data for this thread_id
        db.query(Application).filter(
            Application.gmail_thread_id == "test-thread-autofill-123"
        ).delete(synchronize_session=False)
        db.commit()

        # Test with sender, subject, and body_text for auto-extraction
        response = client.post(
            "/applications/from-email",
            json={
                "thread_id": "test-thread-autofill-123",
                "sender": "Careers Team <careers@openai.com>",
                "subject": "Your Application for Research Engineer role at OpenAI",
                "body_text": "Thank you for applying for the Research Engineer position at OpenAI!",
            },
        )

        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify company was extracted (could be "openai" or "Careers Team")
        assert data["company"].lower() in [
            "openai",
            "careers",
            "careers team",
        ], f"Unexpected company: {data['company']}"

        # Verify role was extracted
        assert (
            "Engineer" in data["role"]
        ), f"Expected 'Engineer' in role, got: {data['role']}"

        # Verify source defaults to Email
        assert data["source"] in [
            "Email",
            "email",
        ], f"Unexpected source: {data['source']}"

        print(
            f"✅ Test passed: /from-email endpoint auto-extracted: company={data['company']}, role={data['role']}, source={data['source']}"
        )

        return data
    finally:
        db.close()


if __name__ == "__main__":
    print("Running application tests...")
    test_upsert_application_from_email()
    test_upsert_application_by_thread_id()
    test_no_application_without_metadata()
    test_from_email_endpoint_autofill()
    print("✅ All tests passed!")
