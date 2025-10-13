"""
Gmail reply metrics computation.
Analyzes thread messages to determine user reply activity.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

EMAIL_RE = re.compile(r"<([^>]+)>")


def _extract_email(addr: str) -> str:
    """Extract email from 'Name <email@domain.com>' format."""
    m = EMAIL_RE.search(addr or "")
    return (m.group(1) if m else addr or "").strip().lower()


def classify_direction(raw_msg: Dict[str, Any], user_email: str) -> str:
    """Return 'outbound' if From == user_email, else 'inbound'."""
    headers = {
        h.get("name", "").lower(): h.get("value", "")
        for h in raw_msg.get("payload", {}).get("headers", [])
    }
    from_h = headers.get("from", "")
    from_addr = _extract_email(from_h)
    return "outbound" if from_addr == user_email else "inbound"


def msg_received_at(raw_msg: Dict[str, Any]) -> Optional[datetime]:
    """Prefer internalDate (ms) or Date header."""
    if "internalDate" in raw_msg:
        try:
            ms = int(raw_msg["internalDate"])
            return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
        except Exception:
            pass

    headers = {
        h.get("name", "").lower(): h.get("value", "")
        for h in raw_msg.get("payload", {}).get("headers", [])
    }
    date_h = headers.get("date")
    if not date_h:
        return None

    try:
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(date_h)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def compute_thread_reply_metrics(
    raw_messages: Iterable[Dict[str, Any]], user_email: str
) -> Dict[str, Any]:
    """
    Given all Gmail API messages in a thread, compute reply metrics for the user.

    Returns:
        {
            "first_user_reply_at": ISO datetime or None,
            "last_user_reply_at": ISO datetime or None,
            "user_reply_count": int,
            "replied": bool
        }
    """
    first_out: Optional[datetime] = None
    last_out: Optional[datetime] = None
    out_count = 0

    # Ensure stable iteration
    msgs = list(raw_messages)

    # Sort by received order
    msgs.sort(
        key=lambda m: (msg_received_at(m) or datetime.min.replace(tzinfo=timezone.utc))
    )

    for m in msgs:
        if classify_direction(m, user_email) == "outbound":
            ts = msg_received_at(m)
            if not ts:
                continue
            out_count += 1
            if not first_out or ts < first_out:
                first_out = ts
            if not last_out or ts > last_out:
                last_out = ts

    replied = out_count > 0

    return {
        "first_user_reply_at": first_out.isoformat() if first_out else None,
        "last_user_reply_at": last_out.isoformat() if last_out else None,
        "user_reply_count": out_count,
        "replied": replied,
    }
