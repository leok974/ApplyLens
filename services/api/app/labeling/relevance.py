"""Time-relevance extraction for emails (expires_at, event_time).

This module parses email content to extract time-sensitive information:
- Promo expiration dates (e.g., "Valid through 12/31/2024")
- Event times (e.g., "Meeting on January 15 at 3:00 PM")

These fields enable:
- Auto-hiding expired promos
- Prioritizing time-sensitive emails
- Building "upcoming events" digests
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

# Regex patterns for expiration date detection
EXPIRY_PATTERN = re.compile(
    r"\b(valid\s+thru|valid\s+through|expires?|expire\s+on|by|until)\b\s*(?P<date>[\w/,\-\s]+)",
    re.IGNORECASE
)

# Date extraction patterns
DATE_PATTERN = re.compile(r"\b(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b")
MONTH_DAY_YEAR = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{1,2}),?\s*(\d{4})?\b", re.IGNORECASE)

# Event time patterns
EVENT_PATTERN = re.compile(
    r"\b(on|at|scheduled\s+for)\s+(?P<date>\w{3,9}\s+\d{1,2}(?:,?\s*\d{4})?)\s*(?:at\s+(?P<time>\d{1,2}:\d{2}\s*(?:am|pm)?))?",
    re.IGNORECASE
)

WEEKDAY_PATTERN = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE
)

# Month name to number mapping
MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def parse_promo_expiry(text: str, received_at_iso: str) -> Optional[datetime]:
    """Extract promotion expiration date from email content.
    
    Looks for patterns like:
        - "Valid through 12/31/2024"
        - "Expires December 31, 2024"
        - "Offer ends by 12/31"
        
    Falls back to received_at + 7 days heuristic if no explicit date found.
    
    Args:
        text: Email subject + body combined
        received_at_iso: ISO timestamp of when email was received
        
    Returns:
        datetime object (timezone-aware) or None if no expiry detected
        
    Examples:
        >>> parse_promo_expiry("Sale ends 12/31/2024", "2024-12-15T10:00:00Z")
        datetime(2024, 12, 31, 0, 0, tzinfo=timezone.utc)
        
        >>> parse_promo_expiry("Limited time offer!", "2024-12-15T10:00:00Z")
        datetime(2024, 12, 22, 10, 0, tzinfo=timezone.utc)  # +7 days
    """
    if not text:
        return None
    
    # Try to find explicit expiry date
    match = EXPIRY_PATTERN.search(text)
    if match:
        date_str = match.group("date")
        
        # Try MM/DD/YYYY format
        date_match = DATE_PATTERN.search(date_str)
        if date_match:
            try:
                parts = date_match.group(1).split("/")
                mm, dd = int(parts[0]), int(parts[1])
                yy = int(parts[2]) if len(parts) > 2 else datetime.now(timezone.utc).year
                
                # Handle 2-digit year
                if yy < 100:
                    yy += 2000
                
                return datetime(yy, mm, dd, 23, 59, 59, tzinfo=timezone.utc)
            except (ValueError, IndexError):
                pass
        
        # Try Month DD, YYYY format
        month_match = MONTH_DAY_YEAR.search(date_str)
        if month_match:
            try:
                month_name = month_match.group(1).lower()[:3]
                day = int(month_match.group(2))
                year = int(month_match.group(3)) if month_match.group(3) else datetime.now(timezone.utc).year
                
                month = MONTH_MAP.get(month_name)
                if month:
                    return datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc)
            except (ValueError, KeyError):
                pass
    
    # Fallback heuristic: promos typically valid for 7 days
    try:
        received_dt = datetime.fromisoformat(received_at_iso.replace("Z", "+00:00"))
        return received_dt + timedelta(days=7)
    except Exception:
        # Last resort: 7 days from now
        return datetime.now(timezone.utc) + timedelta(days=7)


def parse_event_time(text: str, received_at_iso: str) -> Optional[datetime]:
    """Extract event time from invitation emails.
    
    Looks for patterns like:
        - "Meeting on January 15 at 3:00 PM"
        - "Scheduled for Dec 31, 2024"
        - "Join us on Friday at 10:00 AM"
        
    Args:
        text: Email subject + body combined
        received_at_iso: ISO timestamp of when email was received
        
    Returns:
        datetime object (timezone-aware) or None if no event found
        
    Examples:
        >>> parse_event_time("Meeting on Jan 15, 2025 at 3:00 PM", "2024-12-15T10:00:00Z")
        datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc)
        
    Note:
        Current implementation is minimal - can be enhanced with:
        - Timezone parsing
        - Recurring event detection
        - Multi-day event handling
    """
    if not text:
        return None
    
    match = EVENT_PATTERN.search(text)
    if not match:
        return None
    
    date_str = match.group("date")
    time_str = match.group("time")
    
    # Parse date part
    month_match = MONTH_DAY_YEAR.search(date_str)
    if not month_match:
        return None
    
    try:
        month_name = month_match.group(1).lower()[:3]
        day = int(month_match.group(2))
        year = int(month_match.group(3)) if month_match.group(3) else datetime.now(timezone.utc).year
        
        month = MONTH_MAP.get(month_name)
        if not month:
            return None
        
        # Parse time part (if present)
        hour, minute = 0, 0
        if time_str:
            time_parts = time_str.lower().replace("am", "").replace("pm", "").strip().split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            
            # Handle PM
            if "pm" in time_str.lower() and hour < 12:
                hour += 12
            elif "am" in time_str.lower() and hour == 12:
                hour = 0
        
        return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
        
    except (ValueError, KeyError, IndexError):
        return None


def should_auto_hide(doc: dict) -> bool:
    """Determine if email should be auto-hidden based on expiration.
    
    Args:
        doc: Email document with expires_at and received_at fields
        
    Returns:
        True if expires_at is in the past, False otherwise
    """
    expires = doc.get("expires_at")
    if not expires:
        return False
    
    try:
        expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return expires_dt < now
    except Exception:
        return False


def time_to_expiry_days(doc: dict) -> Optional[float]:
    """Calculate days until expiration.
    
    Args:
        doc: Email document with expires_at field
        
    Returns:
        Days until expiry (negative if expired) or None
    """
    expires = doc.get("expires_at")
    if not expires:
        return None
    
    try:
        expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = expires_dt - now
        return delta.total_seconds() / 86400
    except Exception:
        return None


def is_expiring_soon(doc: dict, threshold_days: int = 3) -> bool:
    """Check if email is expiring soon.
    
    Args:
        doc: Email document with expires_at field
        threshold_days: Days threshold for "soon" (default: 3)
        
    Returns:
        True if expiring within threshold_days
    """
    tte = time_to_expiry_days(doc)
    if tte is None:
        return False
    
    return 0 < tte <= threshold_days
