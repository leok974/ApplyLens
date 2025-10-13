"""
Unit tests for time window parsing.

Tests natural language date phrase parsing for:
- Relative weekday references (before Friday)
- Explicit date formats (mm/dd/yyyy)
- Named month formats (before Oct 15, 2025)
- Relative day counts (in 7 days)
"""

import datetime as dt
from app.logic.timewin import (
    parse_due_cutoff,
    next_weekday,
    parse_relative_days,
    cutoff_from_relative_days,
)


def test_next_weekday_from_wednesday_to_friday():
    """Test finding next Friday from a Wednesday."""
    wed = dt.datetime(2025, 10, 8, 10, 0, 0, tzinfo=dt.timezone.utc)
    friday = next_weekday(wed, 4)  # 4 = Friday
    assert friday.weekday() == 4
    assert friday.day == 10  # Oct 10, 2025 is Friday


def test_next_weekday_same_day():
    """Test finding next Friday when it's already Friday."""
    fri = dt.datetime(2025, 10, 10, 10, 0, 0, tzinfo=dt.timezone.utc)
    friday = next_weekday(fri, 4)  # 4 = Friday
    assert friday.weekday() == 4
    assert friday.day == 10  # Same day


def test_before_friday_to_cutoff_iso():
    """Test parsing 'before Friday' from Wednesday."""
    # Fixed "now": Wed Oct 8, 2025 14:00 UTC (10:00 ET)
    now = dt.datetime(2025, 10, 8, 14, 0, 0, tzinfo=dt.timezone.utc)
    iso = parse_due_cutoff("before Friday", now=now)

    # Should return Friday midnight in ET -> UTC
    # EDT is UTC-4, so midnight Friday ET = 04:00 UTC Friday
    assert iso is not None
    assert iso.startswith("2025-10-10T04:00:00Z")


def test_by_monday_from_saturday():
    """Test parsing 'by Monday' from Saturday."""
    sat = dt.datetime(2025, 10, 11, 14, 0, 0, tzinfo=dt.timezone.utc)
    iso = parse_due_cutoff("by monday", now=sat)

    assert iso is not None
    assert "2025-10-13" in iso  # Oct 13 is Monday


def test_by_explicit_date_mmddyyyy():
    """Test parsing explicit date format 'by 10/15/2025'."""
    now = dt.datetime(2025, 10, 8, 14, 0, 0, tzinfo=dt.timezone.utc)
    iso = parse_due_cutoff("by 10/15/2025", now=now)

    assert iso is not None
    assert "2025-10-15" in iso
    assert iso.endswith("Z")


def test_by_explicit_date_mmdd_current_year():
    """Test parsing date without year (defaults to current year)."""
    now = dt.datetime(2025, 10, 8, 14, 0, 0, tzinfo=dt.timezone.utc)
    iso = parse_due_cutoff("by 12/25", now=now)

    assert iso is not None
    assert "2025-12-25" in iso


def test_by_explicit_date_mmddyy_two_digit_year():
    """Test parsing date with two-digit year."""
    now = dt.datetime(2025, 10, 8, 14, 0, 0, tzinfo=dt.timezone.utc)
    iso = parse_due_cutoff("by 1/1/26", now=now)

    assert iso is not None
    assert "2026-01-01" in iso


def test_before_named_month_with_year():
    """Test parsing 'before Oct 20, 2025'."""
    now = dt.datetime(2025, 10, 8, 14, 0, 0, tzinfo=dt.timezone.utc)
    iso = parse_due_cutoff("before Oct 20, 2025", now=now)

    assert iso is not None
    assert "2025-10-20" in iso


def test_before_named_month_without_year():
    """Test parsing named month without year (defaults to current year)."""
    now = dt.datetime(2025, 10, 8, 14, 0, 0, tzinfo=dt.timezone.utc)
    iso = parse_due_cutoff("before December 31", now=now)

    assert iso is not None
    assert "2025-12-31" in iso


def test_by_named_month_abbreviated():
    """Test parsing abbreviated month names."""
    now = dt.datetime(2025, 10, 8, 14, 0, 0, tzinfo=dt.timezone.utc)
    iso = parse_due_cutoff("by Nov 15, 2025", now=now)

    assert iso is not None
    assert "2025-11-15" in iso


def test_unrecognized_phrase_returns_none():
    """Test that unrecognized phrases return None."""
    now = dt.datetime(2025, 10, 8, 14, 0, 0, tzinfo=dt.timezone.utc)

    assert parse_due_cutoff("yesterday", now=now) is None
    assert parse_due_cutoff("next week", now=now) is None
    assert parse_due_cutoff("asap", now=now) is None
    assert parse_due_cutoff("", now=now) is None
    assert parse_due_cutoff(None, now=now) is None


def test_invalid_date_returns_none():
    """Test that invalid dates return None."""
    now = dt.datetime(2025, 10, 8, 14, 0, 0, tzinfo=dt.timezone.utc)

    # Invalid dates
    assert parse_due_cutoff("by 2/30/2025", now=now) is None
    assert parse_due_cutoff("by 13/1/2025", now=now) is None
    assert parse_due_cutoff("before Feb 30, 2025", now=now) is None


def test_parse_relative_days_in_format():
    """Test parsing 'in N days' format."""
    assert parse_relative_days("in 3 days") == 3
    assert parse_relative_days("in 7 days") == 7
    assert parse_relative_days("in 1 day") == 1


def test_parse_relative_days_within_format():
    """Test parsing 'within N days' format."""
    assert parse_relative_days("within 5 days") == 5
    assert parse_relative_days("within 14 days") == 14


def test_parse_relative_days_next_format():
    """Test parsing 'next N days' format."""
    assert parse_relative_days("next 7 days") == 7
    assert parse_relative_days("next 30 days") == 30


def test_parse_relative_days_not_found():
    """Test that unrecognized relative phrases return None."""
    assert parse_relative_days("before Friday") is None
    assert parse_relative_days("asap") is None
    assert parse_relative_days("") is None


def test_cutoff_from_relative_days():
    """Test converting relative days to absolute cutoff."""
    now = dt.datetime(2025, 10, 8, 14, 0, 0, tzinfo=dt.timezone.utc)
    iso = cutoff_from_relative_days(7, now=now)

    assert iso is not None
    assert "2025-10-15" in iso  # 7 days from Oct 8
    assert iso.endswith("Z")


def test_multiple_weekday_mentions():
    """Test that when multiple weekdays are mentioned, one is parsed."""
    now = dt.datetime(2025, 10, 8, 14, 0, 0, tzinfo=dt.timezone.utc)
    iso = parse_due_cutoff("before Friday or by Monday", now=now)

    # Should parse one of the weekdays (implementation may vary)
    assert iso is not None
    # Just verify it's a valid ISO date
    assert iso.endswith("Z")
    assert "2025-10-" in iso  # October 2025


def test_case_insensitive_parsing():
    """Test that parsing is case-insensitive."""
    now = dt.datetime(2025, 10, 8, 14, 0, 0, tzinfo=dt.timezone.utc)

    iso1 = parse_due_cutoff("before FRIDAY", now=now)
    iso2 = parse_due_cutoff("Before Friday", now=now)
    iso3 = parse_due_cutoff("BEFORE FRIDAY", now=now)

    assert iso1 == iso2 == iso3
    assert "2025-10-10" in iso1


def test_timezone_conversion():
    """Test that dates are properly converted from user TZ to UTC."""
    # Create a datetime in UTC
    now_utc = dt.datetime(2025, 10, 8, 14, 0, 0, tzinfo=dt.timezone.utc)

    # Parse a date (should be interpreted in USER_TZ = EDT = UTC-4)
    iso = parse_due_cutoff("by 10/15/2025", now=now_utc)

    # Midnight Oct 15 in EDT = 04:00 UTC
    assert iso is not None
    assert iso == "2025-10-15T04:00:00Z"
