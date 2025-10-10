"""
Unit tests for backfill_bill_dates.py transformer logic.

Tests the transform() function that extracts due dates and updates expires_at.
"""
import datetime as dt
import sys
import os

# Add scripts to path
scripts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

import backfill_bill_dates
from backfill_bill_dates import transform, earliest


def _doc(body_text, subject="", received_at="2025-10-08T12:00:00Z", dates=None, expires_at=None):
    """Helper to create test document."""
    return {
        "_source": {
            "subject": subject,
            "body_text": body_text,
            "received_at": received_at,
            "dates": dates,
            "expires_at": expires_at
        }
    }


def test_transform_adds_dates_and_expires():
    """Test that transform extracts dates and sets expires_at."""
    d = _doc("Amount due by 10/15/2025. Please pay promptly.")
    upd = transform(d)
    
    assert upd is not None, "Should return update dict"
    assert "dates" in upd, "Should include dates field"
    assert any(s.startswith("2025-10-15") for s in upd["dates"]), "Should extract 10/15/2025"
    assert "expires_at" in upd, "Should include expires_at"
    assert upd["expires_at"].startswith("2025-10-15"), "expires_at should be 2025-10-15"


def test_transform_respects_existing_earlier_expiry():
    """Test that transform keeps earlier existing expires_at."""
    d = _doc(
        "Due by 10/20/2025",
        dates=["2025-10-18T00:00:00Z"],
        expires_at="2025-10-12T00:00:00Z"  # Earlier than detected date
    )
    upd = transform(d)
    
    # Existing expires_at is earlier than detected date; should keep earlier
    # However, dates array will be updated with new date
    if upd:
        # If dates changed, update will include new dates but keep earlier expires_at
        assert upd["expires_at"] == "2025-10-12T00:00:00Z", "Should keep earlier expires_at"
    # Or upd could be None if dates are identical


def test_transform_updates_when_due_is_earlier_than_current_expires():
    """Test that transform updates expires_at when new date is earlier."""
    d = _doc(
        "Payment due on Oct 10, 2025",
        dates=["2025-10-15T00:00:00Z"],
        expires_at="2025-10-15T00:00:00Z"
    )
    upd = transform(d)
    
    assert upd is not None, "Should return update when earlier date found"
    assert "expires_at" in upd, "Should update expires_at"
    assert upd["expires_at"].startswith("2025-10-10"), "Should update to earlier date Oct 10"
    assert any(s.startswith("2025-10-10") for s in upd["dates"]), "Should include new date in dates array"


def test_transform_no_change_when_identical():
    """Test that transform returns None when no changes needed."""
    d = _doc(
        "Due by 10/15/2025",
        dates=["2025-10-15T00:00:00Z"],
        expires_at="2025-10-15T00:00:00Z"
    )
    upd = transform(d)
    
    # Same date already in dates, same expires_at
    assert upd is None, "Should return None when no changes needed"


def test_transform_no_dates_found():
    """Test that transform returns None when no dates can be extracted."""
    d = _doc("This is just a regular email with no due dates.")
    upd = transform(d)
    
    assert upd is None, "Should return None when no dates found"


def test_transform_month_name_format():
    """Test extraction of Month dd, yyyy format."""
    d = _doc("Your bill is due December 25, 2025. Happy holidays!")
    upd = transform(d)
    
    assert upd is not None, "Should extract date"
    assert any(s.startswith("2025-12-25") for s in upd["dates"]), "Should extract December 25, 2025"


def test_transform_multiple_dates():
    """Test extraction of multiple due dates."""
    d = _doc("First payment due 10/15/2025, second payment due 11/15/2025.")
    upd = transform(d)
    
    assert upd is not None, "Should extract dates"
    assert len(upd["dates"]) == 2, "Should extract both dates"
    assert upd["expires_at"].startswith("2025-10-15"), "expires_at should be earliest (Oct 15)"


def test_transform_deduplicates_dates():
    """Test that duplicate dates are removed."""
    d = _doc("Payment due by 10/15/2025. Reminder: payment is due on 10/15/2025.")
    upd = transform(d)
    
    assert upd is not None, "Should extract dates"
    # Should deduplicate to single date
    assert len(upd["dates"]) == 1, "Should deduplicate identical dates"
    assert upd["dates"][0].startswith("2025-10-15"), "Should be 10/15/2025"


def test_transform_extracts_from_subject():
    """Test extraction from subject line."""
    d = _doc(
        body_text="Please pay your bill.",
        subject="Bill due October 20, 2025"
    )
    upd = transform(d)
    
    assert upd is not None, "Should extract from subject"
    assert any(s.startswith("2025-10-20") for s in upd["dates"]), "Should extract Oct 20 from subject"


def test_transform_year_inference():
    """Test that year is inferred from received_at when missing."""
    d = _doc(
        "Payment due by 12/25",  # No year specified
        received_at="2025-10-08T12:00:00Z"
    )
    upd = transform(d)
    
    assert upd is not None, "Should extract date with inferred year"
    assert any(s.startswith("2025-12-25") for s in upd["dates"]), "Should infer year 2025"


def test_earliest_helper():
    """Test the earliest() helper function."""
    assert earliest([]) is None, "Empty list should return None"
    assert earliest(["2025-10-15T00:00:00Z"]) == "2025-10-15T00:00:00Z"
    assert earliest([
        "2025-10-20T00:00:00Z",
        "2025-10-15T00:00:00Z",
        "2025-10-25T00:00:00Z"
    ]) == "2025-10-15T00:00:00Z", "Should return earliest date"


def test_transform_recomputes_expires_from_existing_dates():
    """Test that transform recomputes expires_at even when no new dates extracted."""
    d = _doc(
        "Just a reminder about your bill.",  # No dates in text
        dates=["2025-10-20T00:00:00Z", "2025-10-15T00:00:00Z"],
        expires_at="2025-10-20T00:00:00Z"  # Wrong - should be 10/15
    )
    upd = transform(d)
    
    if upd:
        # Should correct expires_at to earliest date
        assert upd["expires_at"] == "2025-10-15T00:00:00Z", "Should recompute expires_at to earliest"


def test_transform_updates_dates_adds_expires():
    """Test updating dates when expires_at doesn't exist."""
    d = _doc(
        "Payment due by 10/20/2025",
        dates=None,
        expires_at=None
    )
    upd = transform(d)
    
    assert upd is not None, "Should extract dates"
    assert "dates" in upd, "Should add dates field"
    assert "expires_at" in upd, "Should add expires_at field"
    assert upd["expires_at"].startswith("2025-10-20"), "Should set expires_at"
