from app.gmail_service import derive_labels


def test_interview_detection():
    text = "We'd like to schedule an interview with you"
    labels = derive_labels("recruiter@company.com", "Interview for SWE", text)
    assert "interview" in labels


def test_offer_detection():
    labels = derive_labels("hr@co.com", "Offer details", "Congrats on your offer!")
    assert "offer" in labels


def test_newsletter_detection():
    labels = derive_labels("no-reply@co.com", "Monthly update", "Click to unsubscribe")
    assert "newsletter_ads" in labels


def test_rejection_detection():
    s = "We regret to inform you that you were not selected"
    labels = derive_labels("hr@co.com", "Application Status", s)
    assert "rejection" in labels


def test_application_receipt_detection():
    s = "Thank you for your application. We have received your submission."
    labels = derive_labels("jobs@company.com", "Application Confirmation", s)
    assert "application_receipt" in labels


def test_phone_screen_detection():
    s = "Let's schedule a quick phone screen to discuss the role"
    labels = derive_labels("recruiter@company.com", "Quick call", s)
    assert "interview" in labels


def test_onsite_detection():
    s = "Looking forward to your onsite visit next week"
    labels = derive_labels("recruiter@company.com", "Onsite Schedule", s)
    assert "interview" in labels


def test_multiple_labels():
    s = "We received your application and would like to schedule an interview"
    labels = derive_labels("hr@company.com", "Application Update", s)
    assert "application_receipt" in labels
    assert "interview" in labels


def test_no_labels():
    s = "Just following up on our conversation last week"
    labels = derive_labels("person@company.com", "Follow up", s)
    assert len(labels) == 0
