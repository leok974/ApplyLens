"""
Tests for email parsing heuristics module.
"""

from app.services.email_parse import (extract_company, extract_role,
                                      extract_source)


def test_extract_company_from_sender():
    """Test company extraction from sender email."""
    sender = "Careers <careers@openai.com>"
    company = extract_company(sender, "", "")
    assert company.lower() in ["openai", "careers"], f"Got: {company}"
    print(f"✅ Extracted company from sender: {company}")


def test_extract_company_from_body():
    """Test company extraction from email body."""
    sender = "noreply@jobs.example.com"
    body = "Thank you for applying at Anthropic!"
    company = extract_company(sender, body, "")
    assert "Anthropic" in company or "jobs" in company.lower(), f"Got: {company}"
    print(f"✅ Extracted company from body: {company}")


def test_extract_role_from_subject():
    """Test role extraction from subject line."""
    subject = "Your Application for Research Engineer role at OpenAI"
    role = extract_role(subject, "")
    assert "Engineer" in role, f"Got: {role}"
    print(f"✅ Extracted role from subject: {role}")


def test_extract_role_with_position_label():
    """Test role extraction with Position: label."""
    body = "Position: Senior ML Engineer\n\nWe are excited to..."
    role = extract_role("", body)
    assert "ML Engineer" in role or "Senior" in role, f"Got: {role}"
    print(f"✅ Extracted role from body: {role}")


def test_extract_source_lever():
    """Test source detection for Lever ATS."""
    subject = "Application via Lever"
    source = extract_source({}, "", subject, "")
    assert source == "Lever", f"Got: {source}"
    print(f"✅ Detected Lever source: {source}")


def test_extract_source_greenhouse():
    """Test source detection for Greenhouse ATS."""
    sender = "noreply@greenhouse.io"
    source = extract_source({}, sender, "", "")
    assert source == "Greenhouse", f"Got: {source}"
    print(f"✅ Detected Greenhouse source: {source}")


def test_extract_source_linkedin():
    """Test source detection for LinkedIn."""
    body = "You applied to this job through LinkedIn"
    source = extract_source({}, "", "", body)
    assert source == "LinkedIn", f"Got: {source}"
    print(f"✅ Detected LinkedIn source: {source}")


def test_extract_source_default():
    """Test source defaults to Email when no ATS detected."""
    source = extract_source({}, "recruiter@company.com", "Interview", "Let's chat")
    assert source == "Email", f"Got: {source}"
    print(f"✅ Defaulted to Email source: {source}")


def test_full_extraction_pipeline():
    """Test complete extraction from sample email."""
    sample = {
        "sender": "Stripe Careers <careers@stripe.com>",
        "subject": "Your Application for Backend Engineer role",
        "body": "Thank you for applying to Stripe for the Backend Engineer position.",
        "headers": {},
    }

    company = extract_company(sample["sender"], sample["body"], sample["subject"])
    role = extract_role(sample["subject"], sample["body"])
    source = extract_source(
        sample["headers"], sample["sender"], sample["subject"], sample["body"]
    )

    assert company.lower() in ["stripe", "stripe careers"], f"Company: {company}"
    assert "Engineer" in role, f"Role: {role}"
    assert source == "Email", f"Source: {source}"

    print("✅ Full pipeline extraction:")
    print(f"   Company: {company}")
    print(f"   Role: {role}")
    print(f"   Source: {source}")


if __name__ == "__main__":
    print("Running email parsing tests...\n")
    test_extract_company_from_sender()
    test_extract_company_from_body()
    test_extract_role_from_subject()
    test_extract_role_with_position_label()
    test_extract_source_lever()
    test_extract_source_greenhouse()
    test_extract_source_linkedin()
    test_extract_source_default()
    test_full_extraction_pipeline()
    print("\n✅ All email parsing tests passed!")
