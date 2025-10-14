"""
Due date extraction module for bill and payment emails.

Extracts due dates from email text using robust regex patterns.
Supports multiple date formats:
- mm/dd or mm/dd/yyyy (e.g., "10/15" or "10/15/2025")
- Month dd, yyyy (e.g., "Oct 15, 2025")
- dd Month yyyy (e.g., "15 Oct 2025")

Looks for dates near keywords like "due", "payment due", "amount due".
"""

import datetime as dt
import re
from typing import List, Optional

# Regex pattern to find due date sentences
# Looks for 'due' keyword followed by a date within ~80 characters
DUE_SENTENCE_RX = re.compile(
    r"""(?P<prefix>\b(due|pay(?:ment)?\s*(?:is)?\s*due|amount\s*due|due\s*on|due\s*by)\b
         [^\.:\n\r]{0,80}?)                           # up to ~80 chars after 'due'
         (?P<date>(?:[A-Z][a-z]{2,12}\s+\d{1,2},?\s*\d{0,4})  # Oct 15, 2025 or December 25 (year optional)
            |(?:\d{1,2}/\d{1,2}(?:/\d{2,4})?)                 # 10/15 or 10/15/2025
            |(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*,?\s*\d{0,4}) # 15 Oct 2025
         )""",
    re.I | re.X,
)

# Month name to number mapping
MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _coerce_date_token(tok: str, received_at_utc: dt.datetime) -> Optional[dt.datetime]:
    """
    Parse a date token string into a datetime object.

    Args:
        tok: Date string to parse (e.g., "10/15/2025", "Oct 15, 2025")
        received_at_utc: Email received timestamp (used for default year)

    Returns:
        Parsed datetime in UTC or None if parsing fails

    Examples:
        >>> recv = dt.datetime(2025, 10, 8, tzinfo=dt.timezone.utc)
        >>> _coerce_date_token("10/15/2025", recv)
        datetime.datetime(2025, 10, 15, 0, 0, tzinfo=datetime.timezone.utc)

        >>> _coerce_date_token("Oct 15", recv)  # Uses year from recv
        datetime.datetime(2025, 10, 15, 0, 0, tzinfo=datetime.timezone.utc)
    """
    t = tok.strip().replace(",", "")

    # Format 1: 10/15 or 10/15/2025
    m = re.match(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$", t)
    if m:
        mm, dd, yy = int(m.group(1)), int(m.group(2)), m.group(3)

        if yy is None:
            year = received_at_utc.year
        elif len(yy) == 2:
            year = 2000 + int(yy)
        else:
            year = int(yy)

        try:
            return dt.datetime(year, mm, dd, tzinfo=dt.timezone.utc)
        except ValueError:
            return None

    # Format 2: Oct 15 2025 or "by Oct 15 2025"
    m = re.match(
        r"^(?:(?:by|on)\s+)?([A-Za-z]{3,})\s+(\d{1,2})(?:\s+(\d{4}))?$", t, re.I
    )
    if m:
        mon = MONTHS.get(m.group(1)[:3].lower())
        dd = int(m.group(2))
        yy = m.group(3)
        year = int(yy) if yy else received_at_utc.year

        if mon:
            try:
                return dt.datetime(year, mon, dd, tzinfo=dt.timezone.utc)
            except ValueError:
                return None

    # Format 3: 15 Oct 2025
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3,})(?:\s+(\d{4}))?$", t, re.I)
    if m:
        dd = int(m.group(1))
        mon = MONTHS.get(m.group(2)[:3].lower())
        yy = m.group(3)
        year = int(yy) if yy else received_at_utc.year

        if mon:
            try:
                return dt.datetime(year, mon, dd, tzinfo=dt.timezone.utc)
            except ValueError:
                return None

    # Format 4: Oct 15, 2025 (comma removed earlier)
    m = re.match(r"^([A-Za-z]{3,})\s+(\d{1,2})\s+(\d{4})$", t)
    if m:
        mon = MONTHS.get(m.group(1)[:3].lower())
        dd = int(m.group(2))
        year = int(m.group(3))

        if mon:
            try:
                return dt.datetime(year, mon, dd, tzinfo=dt.timezone.utc)
            except ValueError:
                return None

    return None


def extract_due_dates(text: str, received_at_utc: dt.datetime) -> List[str]:
    """
    Extract all due dates from email text.

    Returns ISO8601 Z timestamps for due dates detected near 'due' keywords.
    Results are deduplicated and sorted chronologically.

    Args:
        text: Email body text to search
        received_at_utc: Email received timestamp (for default year inference)

    Returns:
        List of ISO 8601 timestamp strings (UTC, Z suffix)

    Examples:
        >>> recv = dt.datetime(2025, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
        >>> text = "Payment is due by 10/15/2025. Please pay on time."
        >>> extract_due_dates(text, recv)
        ['2025-10-15T00:00:00Z']

        >>> text = "Due by Oct 20, 2025. Reminder: amount due on 10/15/2025."
        >>> extract_due_dates(text, recv)
        ['2025-10-15T00:00:00Z', '2025-10-20T00:00:00Z']
    """
    if not text:
        return []

    hits = []
    for m in DUE_SENTENCE_RX.finditer(text):
        date_str = m.group("date")
        d = _coerce_date_token(date_str, received_at_utc)
        if d:
            # Convert to ISO 8601 with Z suffix
            iso_str = d.isoformat().replace("+00:00", "Z")
            hits.append(iso_str)

    # Deduplicate and sort chronologically
    unique_dates = sorted(list(set(hits)))
    return unique_dates


def extract_earliest_due_date(text: str, received_at_utc: dt.datetime) -> Optional[str]:
    """
    Extract the earliest due date from email text.

    Convenience function that returns just the first (earliest) due date found.
    Useful for setting expires_at field on bill emails.

    Args:
        text: Email body text to search
        received_at_utc: Email received timestamp

    Returns:
        ISO 8601 timestamp string for earliest date, or None if no dates found

    Example:
        >>> recv = dt.datetime(2025, 10, 8, tzinfo=dt.timezone.utc)
        >>> text = "Due by 10/20. Reminder: pay by 10/15."
        >>> extract_earliest_due_date(text, recv)
        '2025-10-15T00:00:00Z'
    """
    dates = extract_due_dates(text, received_at_utc)
    return dates[0] if dates else None


def extract_due_dates_from_subject(
    subject: str, received_at_utc: dt.datetime
) -> List[str]:
    """
    Extract due dates specifically from email subject line.

    Uses same patterns but may have stricter requirements since subjects
    are shorter and more structured.

    Args:
        subject: Email subject line
        received_at_utc: Email received timestamp

    Returns:
        List of ISO 8601 timestamp strings

    Example:
        >>> recv = dt.datetime(2025, 10, 8, tzinfo=dt.timezone.utc)
        >>> subject = "Your bill is due by 10/15/2025"
        >>> extract_due_dates_from_subject(subject, recv)
        ['2025-10-15T00:00:00Z']
    """
    return extract_due_dates(subject, received_at_utc)


def is_bill_related(subject: str, body_text: str) -> bool:
    """
    Quick heuristic to check if email is bill/payment related.

    Looks for keywords like: bill, invoice, payment, statement, account due.

    Args:
        subject: Email subject
        body_text: Email body

    Returns:
        True if email appears to be bill-related

    Example:
        >>> is_bill_related("Your monthly statement", "Amount due: $50")
        True

        >>> is_bill_related("Newsletter", "Check out our products")
        False
    """
    combined = f"{subject} {body_text}".lower()

    bill_keywords = [
        "bill",
        "invoice",
        "statement",
        "payment",
        "amount due",
        "account due",
        "balance due",
        "pay by",
        "payment reminder",
        "overdue",
        "past due",
        "payment required",
    ]

    return any(kw in combined for kw in bill_keywords)


def extract_money_amounts(text: str) -> List[dict]:
    """
    Extract money amounts from email text.

    Finds patterns like: $50, $1,234.56, USD 100.00

    Args:
        text: Email text to search

    Returns:
        List of dicts with 'amount' (float) and 'currency' (str)

    Example:
        >>> extract_money_amounts("Total due: $125.50")
        [{'amount': 125.5, 'currency': 'USD'}]
    """
    if not text:
        return []

    amounts = []

    # Pattern 1: $123.45 or $1,234.56
    for m in re.finditer(r"\$\s*([\d,]+\.?\d*)", text):
        amount_str = m.group(1).replace(",", "")
        try:
            amount = float(amount_str)
            amounts.append({"amount": amount, "currency": "USD"})
        except ValueError:
            pass

    # Pattern 2: USD 123.45 or EUR 50.00
    for m in re.finditer(r"\b([A-Z]{3})\s+([\d,]+\.?\d*)", text):
        currency = m.group(1)
        amount_str = m.group(2).replace(",", "")
        try:
            amount = float(amount_str)
            amounts.append({"amount": amount, "currency": currency})
        except ValueError:
            pass

    # Deduplicate while preserving order
    seen = set()
    unique_amounts = []
    for amt in amounts:
        key = (amt["amount"], amt["currency"])
        if key not in seen:
            seen.add(key)
            unique_amounts.append(amt)

    return unique_amounts
