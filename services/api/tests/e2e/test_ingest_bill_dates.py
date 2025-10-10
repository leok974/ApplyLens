"""
E2E tests for bill email ingestion with due date extraction.

Tests the complete flow of normalizing a Gmail message and extracting
due dates into the dates[] array and expires_at field.
"""
import base64
import datetime as dt
import pytest
from app.ingest.due_dates import extract_due_dates, extract_earliest_due_date, extract_money_amounts


def enc(s: str) -> str:
    """Encode string to base64 for Gmail API format."""
    return base64.urlsafe_b64encode(s.encode()).decode()


def sample_bill_message():
    """Create a sample bill email in Gmail API format."""
    return {
        "id": "bill123",
        "threadId": "t1",
        "internalDate": "1728388800000",  # Oct 8, 2025 10:00:00 UTC
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Your statement is ready — amount due by 10/15/2025"},
                {"name": "From", "value": "Billing <acct@power.example.com>"},
                {"name": "Date", "value": "Wed, 08 Oct 2025 10:00:00 +0000"},
                {"name": "To", "value": "user@example.com"}
            ],
            "mimeType": "text/plain",
            "body": {
                "data": enc("Amount due by 10/15/2025. Pay online at power.example.com. Total: $125.50")
            }
        }
    }


def sample_bill_with_multiple_dates():
    """Create bill with multiple payment dates."""
    body_text = """
    Your credit card statement is ready.
    
    Minimum payment due: 10/15/2025
    Full balance due: 10/25/2025
    
    Minimum: $50.00
    Full balance: $1,234.56
    """
    
    return {
        "id": "bill_multi",
        "threadId": "t2",
        "internalDate": "1728388800000",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Credit Card Statement"},
                {"name": "From", "value": "Credit Card <statements@bank.example.com>"},
                {"name": "Date", "value": "Wed, 08 Oct 2025 10:00:00 +0000"}
            ],
            "mimeType": "text/plain",
            "body": {"data": enc(body_text)}
        }
    }


def test_extract_due_dates_from_bill():
    """Test extracting due dates from bill email."""
    msg = sample_bill_message()
    recv_timestamp = int(msg["internalDate"]) // 1000
    received_dt = dt.datetime.utcfromtimestamp(recv_timestamp).replace(tzinfo=dt.timezone.utc)
    
    # Decode body
    body_b64 = msg["payload"]["body"]["data"]
    body_text = base64.urlsafe_b64decode(body_b64).decode('utf-8')
    
    # Extract subject
    headers = msg["payload"]["headers"]
    subject = next(h["value"] for h in headers if h["name"] == "Subject")
    
    # Extract dates from body
    dates = extract_due_dates(body_text, received_dt)
    
    assert len(dates) == 1
    assert dates[0] == "2025-10-15T00:00:00Z"
    
    # Also check subject
    subject_dates = extract_due_dates(subject, received_dt)
    assert len(subject_dates) == 1
    assert subject_dates[0] == "2025-10-15T00:00:00Z"


def test_extract_earliest_date_for_expires_at():
    """Test that earliest date can be used for expires_at field."""
    msg = sample_bill_with_multiple_dates()
    recv_timestamp = int(msg["internalDate"]) // 1000
    received_dt = dt.datetime.utcfromtimestamp(recv_timestamp).replace(tzinfo=dt.timezone.utc)
    
    # Decode body
    body_b64 = msg["payload"]["body"]["data"]
    body_text = base64.urlsafe_b64decode(body_b64).decode('utf-8')
    
    # Extract dates
    dates = extract_due_dates(body_text, received_dt)
    earliest = extract_earliest_due_date(body_text, received_dt)
    
    # Should have both dates
    assert len(dates) == 2
    assert "2025-10-15T00:00:00Z" in dates
    assert "2025-10-25T00:00:00Z" in dates
    
    # Earliest should be first date
    assert earliest == "2025-10-15T00:00:00Z"


def test_extract_money_amounts_from_bill():
    """Test extracting money amounts from bill email."""
    msg = sample_bill_message()
    
    # Decode body
    body_b64 = msg["payload"]["body"]["data"]
    body_text = base64.urlsafe_b64decode(body_b64).decode('utf-8')
    
    # Extract money amounts
    amounts = extract_money_amounts(body_text)
    
    assert len(amounts) == 1
    assert amounts[0] == {'amount': 125.5, 'currency': 'USD'}


def test_bill_doc_structure():
    """Test that bill document would have correct structure for ES."""
    msg = sample_bill_message()
    recv_timestamp = int(msg["internalDate"]) // 1000
    received_dt = dt.datetime.utcfromtimestamp(recv_timestamp).replace(tzinfo=dt.timezone.utc)
    
    # Extract fields
    headers = msg["payload"]["headers"]
    subject = next(h["value"] for h in headers if h["name"] == "Subject")
    sender = next(h["value"] for h in headers if h["name"] == "From")
    
    body_b64 = msg["payload"]["body"]["data"]
    body_text = base64.urlsafe_b64decode(body_b64).decode('utf-8')
    
    # Extract due dates and money
    dates = extract_due_dates(body_text, received_dt)
    earliest = extract_earliest_due_date(body_text, received_dt)
    money_amounts = extract_money_amounts(body_text)
    
    # Build document structure (simulating what would be sent to ES)
    doc = {
        "gmail_id": msg["id"],
        "thread_id": msg["threadId"],
        "subject": subject,
        "sender": sender,
        "body_text": body_text,
        "received_at": received_dt.isoformat().replace("+00:00", "Z"),
        "dates": dates,  # Array of all due dates
        "expires_at": earliest,  # Earliest due date
        "money_amounts": money_amounts,
        "category": "bills",  # Would be classified
    }
    
    # Verify structure
    assert "dates" in doc
    assert isinstance(doc["dates"], list)
    assert len(doc["dates"]) > 0
    
    assert "expires_at" in doc
    assert doc["expires_at"] == "2025-10-15T00:00:00Z"
    
    assert "money_amounts" in doc
    assert len(doc["money_amounts"]) > 0


def test_multipart_bill_message():
    """Test extracting from multipart email (common for HTML emails)."""
    msg = {
        "id": "bill_multi",
        "threadId": "t3",
        "internalDate": "1728388800000",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Bill due Oct 20, 2025"},
                {"name": "From", "value": "service@utility.com"}
            ],
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": enc("Payment due by Oct 20, 2025. Amount: $75.00")
                    }
                },
                {
                    "mimeType": "text/html",
                    "body": {
                        "data": enc("<html><body>Payment due by Oct 20, 2025</body></html>")
                    }
                }
            ]
        }
    }
    
    recv_timestamp = int(msg["internalDate"]) // 1000
    received_dt = dt.datetime.utcfromtimestamp(recv_timestamp).replace(tzinfo=dt.timezone.utc)
    
    # Extract from plain text part
    text_part = msg["payload"]["parts"][0]
    body_b64 = text_part["body"]["data"]
    body_text = base64.urlsafe_b64decode(body_b64).decode('utf-8')
    
    dates = extract_due_dates(body_text, received_dt)
    
    assert len(dates) == 1
    assert dates[0] == "2025-10-20T00:00:00Z"


def test_bill_without_year_defaults_to_received_year():
    """Test that date without year uses email received year."""
    # Email received in 2025
    msg = {
        "id": "bill_noyear",
        "threadId": "t4",
        "internalDate": "1728388800000",  # Oct 8, 2025
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Bill due 10/15"},
                {"name": "From", "value": "billing@example.com"}
            ],
            "body": {
                "data": enc("Payment due by 10/15. Thank you.")
            }
        }
    }
    
    recv_timestamp = int(msg["internalDate"]) // 1000
    received_dt = dt.datetime.utcfromtimestamp(recv_timestamp).replace(tzinfo=dt.timezone.utc)
    
    body_b64 = msg["payload"]["body"]["data"]
    body_text = base64.urlsafe_b64decode(body_b64).decode('utf-8')
    
    dates = extract_due_dates(body_text, received_dt)
    
    # Should default to 2025 (year from received_dt)
    assert len(dates) == 1
    assert dates[0].startswith("2025-10-15")


def test_no_dates_returns_empty_arrays():
    """Test that email without due dates returns empty arrays."""
    msg = {
        "id": "not_bill",
        "threadId": "t5",
        "internalDate": "1728388800000",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Welcome to our service"},
                {"name": "From", "value": "welcome@example.com"}
            ],
            "body": {
                "data": enc("Thank you for signing up! No due dates here.")
            }
        }
    }
    
    recv_timestamp = int(msg["internalDate"]) // 1000
    received_dt = dt.datetime.utcfromtimestamp(recv_timestamp).replace(tzinfo=dt.timezone.utc)
    
    body_b64 = msg["payload"]["body"]["data"]
    body_text = base64.urlsafe_b64decode(body_b64).decode('utf-8')
    
    dates = extract_due_dates(body_text, received_dt)
    earliest = extract_earliest_due_date(body_text, received_dt)
    
    assert dates == []
    assert earliest is None


def test_combined_subject_and_body_extraction():
    """Test extracting dates from both subject and body."""
    msg = {
        "id": "bill_combo",
        "threadId": "t6",
        "internalDate": "1728388800000",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Statement ready - due 10/15"},
                {"name": "From", "value": "billing@example.com"}
            ],
            "body": {
                "data": enc("Your statement shows payment due by October 15, 2025. Please pay promptly.")
            }
        }
    }
    
    recv_timestamp = int(msg["internalDate"]) // 1000
    received_dt = dt.datetime.utcfromtimestamp(recv_timestamp).replace(tzinfo=dt.timezone.utc)
    
    # Extract from subject
    headers = msg["payload"]["headers"]
    subject = next(h["value"] for h in headers if h["name"] == "Subject")
    subject_dates = extract_due_dates(subject, received_dt)
    
    # Extract from body
    body_b64 = msg["payload"]["body"]["data"]
    body_text = base64.urlsafe_b64decode(body_b64).decode('utf-8')
    body_dates = extract_due_dates(body_text, received_dt)
    
    # Both should find the same date
    assert len(subject_dates) == 1
    assert len(body_dates) == 1
    assert subject_dates[0].startswith("2025-10-15")
    assert body_dates[0].startswith("2025-10-15")


@pytest.mark.asyncio
async def test_integration_with_classification():
    """Test that due dates integrate with bill classification."""
    from app.ingest.due_dates import is_bill_related
    
    msg = sample_bill_message()
    
    # Extract fields
    headers = msg["payload"]["headers"]
    subject = next(h["value"] for h in headers if h["name"] == "Subject")
    
    body_b64 = msg["payload"]["body"]["data"]
    body_text = base64.urlsafe_b64decode(body_b64).decode('utf-8')
    
    # Should be classified as bill
    assert is_bill_related(subject, body_text) is True
    
    # Should have due dates
    recv_dt = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
    dates = extract_due_dates(body_text, recv_dt)
    assert len(dates) > 0
