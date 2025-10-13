"""
Unit tests for due date extraction.

Tests the robust Python-side due date parser that extracts dates from
bill and payment email text.
"""

import datetime as dt
from app.ingest.due_dates import (
    extract_due_dates,
    extract_earliest_due_date,
    extract_due_dates_from_subject,
    is_bill_related,
    extract_money_amounts,
    _coerce_date_token,
)


def test_extract_mmddyyyy_after_due():
    """Test extracting mm/dd/yyyy format after 'due' keyword."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "Your payment is due by 10/15/2025. Please avoid late fees."
    dates = extract_due_dates(txt, recv)

    assert len(dates) == 1
    assert dates[0] == "2025-10-15T00:00:00Z"


def test_extract_mmdd_without_year():
    """Test extracting mm/dd format (defaults to received year)."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "Payment due by 10/15. Thank you."
    dates = extract_due_dates(txt, recv)

    assert len(dates) == 1
    assert dates[0].startswith("2025-10-15T00:00:00Z")


def test_extract_month_name_format():
    """Test extracting 'Month dd, yyyy' format."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "Amount due on Oct 20, 2025 — thank you!"
    dates = extract_due_dates(txt, recv)

    assert len(dates) == 1
    assert dates[0] == "2025-10-20T00:00:00Z"


def test_extract_month_name_without_year():
    """Test extracting 'Month dd' format (defaults to received year)."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "Payment due by December 25. Happy holidays!"  # Changed to include "due by"
    dates = extract_due_dates(txt, recv)

    assert len(dates) == 1
    assert dates[0].startswith("2025-12-25T00:00:00Z")


def test_extract_dd_month_yyyy_format():
    """Test extracting 'dd Month yyyy' format."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "Payment is due on 15 Oct 2025. Please pay promptly."
    dates = extract_due_dates(txt, recv)

    assert len(dates) == 1
    assert dates[0] == "2025-10-15T00:00:00Z"


def test_multiple_due_dates_sorted():
    """Test that multiple dates are extracted and sorted chronologically."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "Due by 10/20/2025. Reminder: payment due on 10/15/2025."
    dates = extract_due_dates(txt, recv)

    assert len(dates) == 2
    assert dates[0] == "2025-10-15T00:00:00Z"  # Earlier date first
    assert dates[1] == "2025-10-20T00:00:00Z"


def test_duplicate_dates_deduped():
    """Test that duplicate dates are deduplicated."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "Due by 10/15/2025. Reminder: due on 10/15/2025. Pay by 10/15/2025."
    dates = extract_due_dates(txt, recv)

    assert len(dates) == 1
    assert dates[0] == "2025-10-15T00:00:00Z"


def test_no_due_dates_returns_empty():
    """Test that text without due dates returns empty list."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "Thank you for your business. We appreciate your patronage."
    dates = extract_due_dates(txt, recv)

    assert dates == []


def test_empty_text_returns_empty():
    """Test that empty text returns empty list."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)

    assert extract_due_dates("", recv) == []
    assert extract_due_dates(None, recv) == []


def test_invalid_date_ignored():
    """Test that invalid dates (like 2/30) are ignored."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "Payment due by 2/30/2025. Invalid date test."
    dates = extract_due_dates(txt, recv)

    # Should ignore invalid date
    assert len(dates) == 0


def test_extract_earliest_due_date():
    """Test extracting just the earliest due date."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "Due by 10/20/2025. Also due on 10/15/2025. Final due 10/25/2025."  # Changed so all dates are near "due"

    earliest = extract_earliest_due_date(txt, recv)
    assert earliest == "2025-10-15T00:00:00Z"


def test_extract_earliest_no_dates():
    """Test that earliest returns None when no dates found."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "No due dates in this text."

    assert extract_earliest_due_date(txt, recv) is None


def test_extract_from_subject_line():
    """Test extracting due dates from subject line."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    subject = "Your bill is due by 10/15/2025"

    dates = extract_due_dates_from_subject(subject, recv)
    assert len(dates) == 1
    assert dates[0] == "2025-10-15T00:00:00Z"


def test_coerce_date_token_formats():
    """Test the _coerce_date_token helper with various formats."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)

    # Format: 10/15/2025
    d1 = _coerce_date_token("10/15/2025", recv)
    assert d1 == dt.datetime(2025, 10, 15, 0, 0, 0, tzinfo=dt.timezone.utc)

    # Format: 10/15 (uses year from recv)
    d2 = _coerce_date_token("10/15", recv)
    assert d2 == dt.datetime(2025, 10, 15, 0, 0, 0, tzinfo=dt.timezone.utc)

    # Format: Oct 15 2025
    d3 = _coerce_date_token("Oct 15 2025", recv)
    assert d3 == dt.datetime(2025, 10, 15, 0, 0, 0, tzinfo=dt.timezone.utc)

    # Format: 15 Oct 2025
    d4 = _coerce_date_token("15 Oct 2025", recv)
    assert d4 == dt.datetime(2025, 10, 15, 0, 0, 0, tzinfo=dt.timezone.utc)

    # Invalid format
    d5 = _coerce_date_token("invalid", recv)
    assert d5 is None


def test_two_digit_year():
    """Test that two-digit years are interpreted as 20xx."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "Payment due by 10/15/25. Thank you."
    dates = extract_due_dates(txt, recv)

    assert len(dates) == 1
    assert dates[0] == "2025-10-15T00:00:00Z"


def test_case_insensitive_keywords():
    """Test that 'DUE' and 'Due' both work."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)

    txt1 = "DUE BY 10/15/2025"
    dates1 = extract_due_dates(txt1, recv)
    assert len(dates1) == 1

    txt2 = "Due by 10/15/2025"
    dates2 = extract_due_dates(txt2, recv)
    assert len(dates2) == 1

    assert dates1 == dates2


def test_payment_due_variation():
    """Test 'payment due' keyword variation."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "Payment is due by 10/15/2025. Please remit promptly."
    dates = extract_due_dates(txt, recv)

    assert len(dates) == 1
    assert dates[0] == "2025-10-15T00:00:00Z"


def test_amount_due_variation():
    """Test 'amount due' keyword variation."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
    txt = "Amount due on October 20, 2025. Thank you."
    dates = extract_due_dates(txt, recv)

    assert len(dates) == 1
    assert dates[0] == "2025-10-20T00:00:00Z"


def test_is_bill_related_positive():
    """Test bill detection with bill-related keywords."""
    assert is_bill_related("Your monthly bill", "Amount due: $50") is True
    assert is_bill_related("Invoice #12345", "Please pay by Friday") is True
    assert is_bill_related("Account statement", "Balance due") is True
    assert is_bill_related("Payment reminder", "Past due") is True


def test_is_bill_related_negative():
    """Test bill detection with non-bill content."""
    assert is_bill_related("Newsletter", "Check out our products") is False
    assert is_bill_related("Welcome!", "Thanks for signing up") is False
    assert is_bill_related("Meeting invite", "Join us on Zoom") is False


def test_extract_money_amounts_dollar_sign():
    """Test extracting amounts with $ prefix."""
    amounts = extract_money_amounts("Total due: $125.50. Late fee: $10.00")

    assert len(amounts) == 2
    assert amounts[0] == {"amount": 125.5, "currency": "USD"}
    assert amounts[1] == {"amount": 10.0, "currency": "USD"}


def test_extract_money_amounts_with_commas():
    """Test extracting amounts with thousand separators."""
    amounts = extract_money_amounts("Balance: $1,234.56")

    assert len(amounts) == 1
    assert amounts[0] == {"amount": 1234.56, "currency": "USD"}


def test_extract_money_amounts_currency_code():
    """Test extracting amounts with currency codes."""
    amounts = extract_money_amounts("Total: USD 100.50 or EUR 90.00")

    assert len(amounts) == 2
    assert amounts[0] == {"amount": 100.5, "currency": "USD"}
    assert amounts[1] == {"amount": 90.0, "currency": "EUR"}


def test_extract_money_amounts_no_amounts():
    """Test that text without money amounts returns empty list."""
    amounts = extract_money_amounts("No money mentioned here.")
    assert amounts == []


def test_extract_money_amounts_deduplication():
    """Test that duplicate amounts are deduplicated."""
    amounts = extract_money_amounts("Pay $50. Total: $50. Amount: $50.")

    assert len(amounts) == 1
    assert amounts[0] == {"amount": 50.0, "currency": "USD"}


def test_month_abbreviations():
    """Test that month abbreviations are recognized."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)

    months = [
        ("Jan", 1),
        ("Feb", 2),
        ("Mar", 3),
        ("Apr", 4),
        ("May", 5),
        ("Jun", 6),
        ("Jul", 7),
        ("Aug", 8),
        ("Sep", 9),
        ("Sept", 9),
        ("Oct", 10),
        ("Nov", 11),
        ("Dec", 12),
    ]

    for month_name, month_num in months:
        txt = f"Due by {month_name} 15, 2025"
        dates = extract_due_dates(txt, recv)

        assert len(dates) == 1
        expected = f"2025-{month_num:02d}-15T00:00:00Z"
        assert dates[0] == expected


def test_realistic_bill_email():
    """Test with realistic bill email content."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)

    subject = "Your electric bill is ready — amount due by 10/15/2025"
    body = """
    Dear Customer,
    
    Your electric bill for September 2025 is now available.
    
    Amount due: $125.50
    Payment is due by 10/15/2025
    
    To avoid late fees, please pay by the due date.
    
    Thank you,
    Electric Company
    """

    # Extract from subject
    subject_dates = extract_due_dates_from_subject(subject, recv)
    assert len(subject_dates) == 1
    assert subject_dates[0] == "2025-10-15T00:00:00Z"

    # Extract from body
    body_dates = extract_due_dates(body, recv)
    assert len(body_dates) == 1
    assert body_dates[0] == "2025-10-15T00:00:00Z"

    # Check money amounts
    amounts = extract_money_amounts(body)
    assert len(amounts) == 1
    assert amounts[0] == {"amount": 125.5, "currency": "USD"}

    # Check bill detection
    assert is_bill_related(subject, body) is True


def test_earliest_from_multiple_dates():
    """Test that earliest date is selected when multiple dates exist."""
    recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)

    txt = """
    First payment due by 10/15/2025
    Second payment due by 11/15/2025
    Final payment due by 12/15/2025
    """

    earliest = extract_earliest_due_date(txt, recv)
    assert earliest == "2025-10-15T00:00:00Z"
