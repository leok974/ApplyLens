"""
Time window parsing utilities.

Converts natural language date phrases into absolute ISO timestamps.
Supports:
- "before Friday", "by Monday"
- "by 10/15", "before 10/20/2025"
- "before Oct 15, 2025"
"""

import datetime as dt
import re
from typing import Optional

# Default user TZ (can be overridden per-user)
# America/New_York EDT; swap to zoneinfo if needed for production
USER_TZ = dt.timezone(dt.timedelta(hours=-4))

WEEKDAY = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def next_weekday(from_dt: dt.datetime, weekday: int) -> dt.datetime:
    """
    Find the next occurrence of a given weekday.

    Args:
        from_dt: Starting datetime
        weekday: Target weekday (0=Monday, 6=Sunday)

    Returns:
        Datetime for the next occurrence of that weekday

    Note:
        If we're already on that weekday, returns that same day
        (treats "before Friday" as by end of this Friday)
    """
    days_ahead = (weekday - from_dt.weekday()) % 7
    # If days_ahead is 0, we're already on that weekday
    return from_dt + dt.timedelta(days=days_ahead)


def parse_due_cutoff(
    text: str, now: Optional[dt.datetime] = None, tz: dt.timezone = USER_TZ
) -> Optional[str]:
    """
    Parse natural language date phrases into ISO cutoff timestamps.

    Returns an ISO string cutoff (exclusive) for phrases like:
    - "before friday"
    - "by 10/15"
    - "before Oct 20, 2025"

    If not recognized, returns None.

    Args:
        text: Natural language date phrase
        now: Current datetime (defaults to UTC now)
        tz: User timezone (defaults to USER_TZ)

    Returns:
        ISO 8601 timestamp string (UTC) or None if not parsed

    Examples:
        >>> parse_due_cutoff("before Friday")
        '2025-10-10T04:00:00Z'  # Midnight Friday in user TZ -> UTC

        >>> parse_due_cutoff("by 10/15/2025")
        '2025-10-15T04:00:00Z'

        >>> parse_due_cutoff("before Oct 20, 2025")
        '2025-10-20T04:00:00Z'
    """
    text_l = (text or "").lower()

    if not now:
        now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)

    now = now.astimezone(tz)

    # 1) "before <weekday>" or "by <weekday>"
    for name, wd in WEEKDAY.items():
        if f"before {name}" in text_l or f"by {name}" in text_l:
            target = next_weekday(now, wd)
            # cutoff = start of that day in local tz
            cutoff_local = target.replace(hour=0, minute=0, second=0, microsecond=0)
            return (
                cutoff_local.astimezone(dt.timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )

    # 2) Explicit dates: mm/dd(/yy|yyyy)
    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", text_l)
    if m:
        mm, dd, yy = int(m.group(1)), int(m.group(2)), m.group(3)

        if yy is None:
            year = now.year
        elif len(yy) == 2:
            year = 2000 + int(yy)
        else:
            year = int(yy)

        try:
            dt_local = dt.datetime(year, mm, dd, 0, 0, 0, tzinfo=tz)
            return (
                dt_local.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
            )
        except ValueError:
            # Invalid date (e.g., 2/30)
            pass

    # 3) "before <Month> <day>, <year?>"
    m2 = re.search(
        r"\b(before|by)\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:,\s*(\d{4}))?\b",
        text_l,
    )
    if m2:
        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }
        mm = month_map[m2.group(2)[:3]]
        dd = int(m2.group(3))
        year = int(m2.group(4)) if m2.group(4) else now.year

        try:
            dt_local = dt.datetime(year, mm, dd, 0, 0, 0, tzinfo=tz)
            return (
                dt_local.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
            )
        except ValueError:
            # Invalid date
            pass

    return None


def parse_relative_days(text: str) -> Optional[int]:
    """
    Parse relative day phrases like "in 3 days", "within 7 days".

    Args:
        text: Natural language phrase

    Returns:
        Number of days or None if not parsed

    Examples:
        >>> parse_relative_days("in 3 days")
        3

        >>> parse_relative_days("within 7 days")
        7
    """
    text_l = text.lower()

    # "in N days" or "within N days"
    m = re.search(r"\b(?:in|within)\s+(\d+)\s+days?\b", text_l)
    if m:
        return int(m.group(1))

    # "next N days"
    m = re.search(r"\bnext\s+(\d+)\s+days?\b", text_l)
    if m:
        return int(m.group(1))

    return None


def cutoff_from_relative_days(
    days: int, now: Optional[dt.datetime] = None, tz: dt.timezone = USER_TZ
) -> str:
    """
    Convert relative days to absolute ISO cutoff.

    Args:
        days: Number of days from now
        now: Current datetime
        tz: User timezone

    Returns:
        ISO 8601 timestamp string (UTC)

    Example:
        >>> cutoff_from_relative_days(7)
        '2025-10-17T04:00:00Z'  # 7 days from now
    """
    if not now:
        now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)

    now_local = now.astimezone(tz)
    target = now_local + dt.timedelta(days=days)

    # Midnight of target day
    target = target.replace(hour=0, minute=0, second=0, microsecond=0)

    return target.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
