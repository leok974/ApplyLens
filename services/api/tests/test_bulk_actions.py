"""
Test bulk security action endpoints

Tests the bulk quarantine, release, and rescan endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Email


@pytest.fixture
def sample_emails(db: Session):
    """
    Create sample emails in the database for testing.
    Returns list of email IDs.
    """
    emails = []
    for i in range(5):
        email = Email(
            id=f"test-bulk-{i}",
            subject=f"Test Email {i}",
            sender=f"sender{i}@example.com",
            recipient="test@example.com",
            date="2024-01-01",
            raw_body=f"Test body {i}",
            quarantined=False,
            risk_score=50.0
        )
        db.add(email)
        emails.append(email.id)
    
    db.commit()
    return emails


def test_bulk_quarantine(client: TestClient, sample_emails: list[str]):
    """
    Test POST /api/security/bulk/quarantine
    Should set quarantined=True for all provided email IDs.
    """
    # Select first 3 emails
    ids_to_quarantine = sample_emails[:3]
    
    response = client.post(
        "/api/security/bulk/quarantine",
        json=ids_to_quarantine
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should report that 3 emails were quarantined
    assert data["quarantined"] == 3
    assert data["total"] == 3
    
    # Verify emails are actually quarantined in the database
    for email_id in ids_to_quarantine:
        r = client.get(f"/api/security/analyze/{email_id}")
        assert r.status_code == 200
        # Check if email shows as quarantined
        # (depends on your analyze endpoint returning quarantined status)


def test_bulk_release(client: TestClient, sample_emails: list[str], db: Session):
    """
    Test POST /api/security/bulk/release
    Should set quarantined=False for all provided email IDs.
    """
    # First quarantine some emails
    ids_to_test = sample_emails[:3]
    
    # Quarantine them first
    for email_id in ids_to_test:
        email = db.query(Email).filter(Email.id == email_id).first()
        email.quarantined = True
    db.commit()
    
    # Now release them via bulk endpoint
    response = client.post(
        "/api/security/bulk/release",
        json=ids_to_test
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should report that 3 emails were released
    assert data["released"] == 3
    assert data["total"] == 3
    
    # Verify emails are actually released
    for email_id in ids_to_test:
        email = db.query(Email).filter(Email.id == email_id).first()
        assert email.quarantined is False


def test_bulk_rescan(client: TestClient, sample_emails: list[str]):
    """
    Test POST /api/security/bulk/rescan
    Should re-analyze all provided emails and update their risk scores.
    """
    ids_to_rescan = sample_emails[:2]
    
    response = client.post(
        "/api/security/bulk/rescan",
        json=ids_to_rescan
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should report updated count
    assert "updated" in data
    assert "total" in data
    assert data["total"] == 2
    # updated might be less than total if some emails fail analysis
    assert 0 <= data["updated"] <= 2


def test_bulk_quarantine_empty_list(client: TestClient):
    """
    Test that bulk endpoints handle empty ID lists gracefully.
    """
    response = client.post(
        "/api/security/bulk/quarantine",
        json=[]
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["quarantined"] == 0
    assert data["total"] == 0


def test_bulk_quarantine_nonexistent_ids(client: TestClient):
    """
    Test that bulk endpoints handle non-existent email IDs gracefully.
    Should not fail, just skip those IDs.
    """
    fake_ids = ["nonexistent-1", "nonexistent-2"]
    
    response = client.post(
        "/api/security/bulk/quarantine",
        json=fake_ids
    )
    
    assert response.status_code == 200
    data = response.json()
    # Should report 0 quarantined since IDs don't exist
    assert data["quarantined"] == 0
    assert data["total"] == 2


def test_bulk_rescan_partial_failure(client: TestClient, sample_emails: list[str], db: Session):
    """
    Test bulk rescan with mix of valid and invalid IDs.
    Should continue processing even if some emails fail.
    """
    # Mix real and fake IDs
    mixed_ids = [sample_emails[0], "fake-id-1", sample_emails[1], "fake-id-2"]
    
    response = client.post(
        "/api/security/bulk/rescan",
        json=mixed_ids
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should report total count but possibly fewer updates
    assert data["total"] == 4
    # At most 2 real emails could be updated (might be fewer if analysis fails)
    assert 0 <= data["updated"] <= 2


def test_bulk_operations_preserve_other_fields(client: TestClient, sample_emails: list[str], db: Session):
    """
    Test that bulk operations don't accidentally modify other email fields.
    """
    email_id = sample_emails[0]
    
    # Get original email data
    original_email = db.query(Email).filter(Email.id == email_id).first()
    original_subject = original_email.subject
    original_sender = original_email.sender
    original_risk = original_email.risk_score
    
    # Perform bulk quarantine
    client.post("/api/security/bulk/quarantine", json=[email_id])
    
    # Check that only quarantined changed
    email = db.query(Email).filter(Email.id == email_id).first()
    assert email.quarantined is True
    assert email.subject == original_subject
    assert email.sender == original_sender
    # Risk score should be unchanged by quarantine action
    assert email.risk_score == original_risk
    
    # Perform bulk release
    client.post("/api/security/bulk/release", json=[email_id])
    
    # Check that only quarantined changed back
    email = db.query(Email).filter(Email.id == email_id).first()
    assert email.quarantined is False
    assert email.subject == original_subject
    assert email.sender == original_sender
