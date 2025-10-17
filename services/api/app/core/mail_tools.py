"""
Mail tools for chat assistant.

Each tool takes RAG search results and user text, returns a tuple of:
(answer: str, actions: List[dict])

Actions can be integrated with Phase 4 approval system if needed.
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from app.core.rag import rag_search

# Performance caps to avoid LLM overload
TOP_N_FOR_SUMMARY = 50  # Maximum docs to show in summaries


def _format_email(doc: Dict[str, Any]) -> str:
    """Format email document for display."""
    subject = doc.get("subject", "(no subject)")
    sender = doc.get("sender", "?")
    received_at = doc.get("received_at", "")
    email_id = doc.get("id", "?")

    # Truncate long subjects
    if len(subject) > 60:
        subject = subject[:57] + "..."

    # Format date nicely if available
    date_str = received_at
    if received_at:
        try:
            dt = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
            date_str = dt.strftime("%b %d, %Y")
        except:  # noqa: E722
            pass

    return f"• [{subject}] — {sender} — {date_str} (#{email_id})"


def _format_email_with_reason(doc: Dict[str, Any], reason: str = "") -> str:
    """Format email with an explanation of why it was matched."""
    base = _format_email(doc)
    if reason:
        return f"{base}\n  → {reason}"
    return base


def summarize_emails(rag: Dict[str, Any], user_text: str) -> Tuple[str, List[dict]]:
    """
    Provide a concise bullet-point summary of matching emails.

    Args:
        rag: RAG search results with docs
        user_text: Original user query

    Returns:
        (answer, actions) tuple
    """
    # Cap docs to prevent LLM overload
    docs = rag.get("docs") or []
    docs = docs[:TOP_N_FOR_SUMMARY]

    if not docs:
        return ("No emails found matching your query.", [])

    total = rag.get("total", len(docs))
    
    # Show only top 10 in the formatted list
    display_docs = docs[:10]
    lines = [_format_email(d) for d in display_docs]

    answer = f"Found {total} emails. Top matches:\n" + "\n".join(lines)

    if total > len(display_docs):
        answer += f"\n\n(Showing first {len(display_docs)} of {total} matches)"

    return (answer, [])


def find_emails(rag: Dict[str, Any], user_text: str, *, owner_email: str | None = None, k: int = 20) -> Tuple[str, List[dict]]:
    """
    Find and list specific emails with reasons for matching.

    Similar to summarize but may include more context about why each email matched.
    """
    total = int(rag.get("total") or 0)
    docs = rag.get("docs") or []

    # --- fallback: if ES says there ARE hits but docs empty, fetch again with safe defaults
    if total > 0 and not docs:
        # try to re-run with explicit k and match_all fallback
        q = user_text.strip() or "*"
        rag2 = rag_search(
            query=q,
            filters=rag.get("filters") or {},
            k=max(k, 20),
            owner_email=owner_email,
        )
        docs = rag2.get("docs") or []
        total = int(rag2.get("total") or total)

    if not docs:
        return ("No emails found matching your criteria.", [])

    # Limit to top results
    docs = docs[:15]

    # Try to extract specific criteria from user text
    lines = []
    for doc in docs:
        category = doc.get("category", "")
        labels = doc.get("labels", [])
        risk = doc.get("risk_score", 0)

        # Build reason based on what matched
        reasons = []
        if category:
            reasons.append(f"category: {category}")
        if risk >= 80:
            reasons.append(f"high risk: {risk}")
        if labels:
            reasons.append(f"labels: {', '.join(labels[:2])}")

        reason = " | ".join(reasons) if reasons else ""
        lines.append(_format_email_with_reason(doc, reason))

    answer = f"Found {total} matching emails:\n" + "\n".join(lines)

    return (answer, [])


def clean_promos(rag: Dict[str, Any], user_text: str) -> Tuple[str, List[dict]]:
    """
    Propose archiving old promotional emails.

    Respects exceptions mentioned in user text (e.g., "unless Best Buy").
    """
    # Look for promotional emails older than a week
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_ago_iso = week_ago.isoformat()

    candidates = [
        d
        for d in rag["docs"]
        if d.get("category") in ["promotions", "promo"]
        and (d.get("received_at") or "") < week_ago_iso
    ]

    # Extract exceptions from user text
    # e.g., "unless Best Buy" or "except amazon"
    exceptions = []
    exception_patterns = [
        r"unless\s+([A-Za-z0-9\s]+?)(?:\.|$|,)",
        r"except(?:ion)?\s+([A-Za-z0-9\s]+?)(?:\.|$|,)",
        r"keep\s+([A-Za-z0-9\s]+?)(?:\.|$|,)",
        r"save\s+([A-Za-z0-9\s]+?)(?:\.|$|,)",
    ]
    for pattern in exception_patterns:
        matches = re.findall(pattern, user_text, re.IGNORECASE)
        exceptions.extend([m.strip().lower() for m in matches])

    # Filter out exceptions
    filtered = []
    for doc in candidates:
        sender = (doc.get("sender") or "").lower()
        sender_domain = (doc.get("sender_domain") or "").lower()

        # Check if any exception matches sender or domain
        is_exception = any(exc in sender or exc in sender_domain for exc in exceptions)

        if not is_exception:
            filtered.append(doc)

    # Limit to 100 actions
    to_archive = filtered[:100]

    actions = [
        {
            "action": "archive_email",
            "email_id": d["id"],
            "params": {
                "reason": "Old promotional email",
                "category": d.get("category"),
            },
        }
        for d in to_archive
    ]

    if not actions:
        if exceptions:
            return (
                f"No old promos found (respecting exceptions: {', '.join(exceptions)}).",
                [],
            )
        return ("No promotional emails older than a week found.", [])

    exception_note = (
        f" (respecting exceptions: {', '.join(exceptions)})" if exceptions else ""
    )
    answer = f"Found {len(filtered)} promotional emails older than a week{exception_note}. Proposing to archive {len(actions)}."

    return (answer, actions)


def unsubscribe_inactive(rag: Dict[str, Any], user_text: str) -> Tuple[str, List[dict]]:
    """
    Propose unsubscribing from inactive newsletters.

    Heuristic: newsletters not engaged with in 60+ days.
    """
    # Look for newsletter emails
    cutoff = datetime.utcnow() - timedelta(days=60)
    cutoff_iso = cutoff.isoformat()

    # Find newsletters or emails with newsletter label
    candidates = [
        d
        for d in rag["docs"]
        if d.get("category") == "newsletter"
        or "newsletter" in (d.get("labels") or [])
        or "subscription" in (d.get("labels") or [])
    ]

    # Filter by age (assuming old = inactive)
    # In a real system, you'd check engagement metrics (opens, clicks)
    inactive = [d for d in candidates if (d.get("received_at") or "") < cutoff_iso]

    # Limit to 50 unsubscribes
    to_unsubscribe = inactive[:50]

    actions = [
        {
            "action": "unsubscribe_via_header",
            "email_id": d["id"],
            "params": {
                "reason": "Inactive newsletter (60+ days)",
                "sender": d.get("sender"),
            },
        }
        for d in to_unsubscribe
    ]

    if not actions:
        return ("No inactive newsletters found (60+ days old).", [])

    answer = f"Found {len(inactive)} inactive newsletters. Proposing {len(actions)} unsubscribe actions."

    # List a few examples
    if to_unsubscribe[:3]:
        answer += "\n\nExamples:"
        for doc in to_unsubscribe[:3]:
            answer += f"\n{_format_email(doc)}"

    return (answer, actions)


def flag_suspicious(rag: Dict[str, Any], user_text: str) -> Tuple[str, List[dict]]:
    """
    Surface suspicious or high-risk emails with explanations.

    Focuses on recent emails from new/unknown domains.
    """
    # Look for recent high-risk emails
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_ago_iso = week_ago.isoformat()

    suspicious = [
        d
        for d in rag["docs"]
        if (d.get("received_at") or "") >= week_ago_iso
        and (
            (d.get("risk_score") or 0) >= 80
            or d.get("category") == "suspicious"
            or "phishing" in (d.get("labels") or [])
        )
    ]

    if not suspicious:
        return ("No high-risk emails from new domains found in the last week. ✓", [])

    lines = []
    for doc in suspicious[:20]:
        risk = doc.get("risk_score", 0)
        category = doc.get("category", "")
        labels = doc.get("labels", [])

        reasons = []
        if risk >= 90:
            reasons.append(f"🔴 Very high risk ({risk}/100)")
        elif risk >= 80:
            reasons.append(f"🟠 High risk ({risk}/100)")

        if category == "suspicious":
            reasons.append("Suspicious category")

        if "phishing" in labels:
            reasons.append("Possible phishing")

        reason = " | ".join(reasons)
        lines.append(_format_email_with_reason(doc, reason))

    answer = f"⚠️ Found {len(suspicious)} suspicious emails this week:\n" + "\n".join(
        lines
    )

    return (answer, [])


def create_calendar_events(
    rag: Dict[str, Any], user_text: str
) -> Tuple[str, List[dict]]:
    """
    Create calendar event reminders from email content.

    Attempts to extract due dates; defaults to 3 days from now.
    """
    # Look for due date mentions in user text
    days_ahead = 3  # default

    # Try to extract "before Friday", "by Monday", etc.
    day_patterns = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    for day_name, day_num in day_patterns.items():
        if day_name in user_text.lower():
            # Calculate days until that day
            today = datetime.utcnow()
            days_until = (day_num - today.weekday()) % 7
            if days_until == 0:
                days_until = 7  # Next week if it's today
            days_ahead = days_until
            break

    # Also check for "in X days"
    days_match = re.search(r"in\s+(\d+)\s+days?", user_text.lower())
    if days_match:
        days_ahead = int(days_match.group(1))

    due_date = datetime.utcnow() + timedelta(days=days_ahead)

    # Pick top emails to create reminders for
    picks = rag["docs"][:5]

    if not picks:
        return ("No emails found to create reminders for.", [])

    actions = [
        {
            "action": "create_calendar_event",
            "email_id": d["id"],
            "params": {
                "title": d.get("subject", "Email reminder"),
                "when": due_date.isoformat(),
                "description": f"Reminder from email: {d.get('sender')}",
            },
        }
        for d in picks
    ]

    due_str = due_date.strftime("%A, %B %d")
    answer = f"📅 Prepared {len(actions)} calendar reminders for {due_str}:"

    for doc in picks:
        answer += f"\n{_format_email(doc)}"

    return (answer, actions)


def create_tasks(rag: Dict[str, Any], user_text: str) -> Tuple[str, List[dict]]:
    """
    Create tasks from actionable email content.
    """
    # Pick top actionable emails
    picks = rag["docs"][:5]

    if not picks:
        return ("No emails found to create tasks for.", [])

    actions = [
        {
            "action": "create_task",
            "email_id": d["id"],
            "params": {
                "title": d.get("subject", "Task from email"),
                "description": f"From: {d.get('sender')}\nReceived: {d.get('received_at')}",
                "priority": "medium",
            },
        }
        for d in picks
    ]

    answer = f"✅ Prepared {len(actions)} tasks from emails:"

    for doc in picks:
        answer += f"\n{_format_email(doc)}"

    return (answer, actions)


def follow_up(rag: Dict[str, Any], user_text: str) -> Tuple[str, List[dict]]:
    """
    Identify threads needing follow-up and suggest draft replies.
    """
    # Look for emails marked for follow-up or in opportunity category
    candidates = [
        d
        for d in rag["docs"]
        if "needs_reply" in (d.get("labels") or [])
        or d.get("category") == "opportunity"
        or "follow_up" in (d.get("labels") or [])
    ]

    # Also check for recruiter emails or application-related emails
    for doc in rag["docs"]:
        if doc in candidates:
            continue

        sender = (doc.get("sender") or "").lower()
        subject = (doc.get("subject") or "").lower()

        if any(
            kw in sender or kw in subject
            for kw in ["recruiter", "hiring", "interview", "application"]
        ):
            candidates.append(doc)

    # Limit to 10
    to_follow_up = candidates[:10]

    if not to_follow_up:
        return ("No threads marked for follow-up found.", [])

    answer = "💬 Emails needing follow-up:\n"

    for doc in to_follow_up:
        sender = doc.get("sender", "?")
        subject = doc.get("subject", "(no subject)")
        doc.get("received_at", "")

        # Generate simple draft suggestion
        draft = f'Hi,\n\nFollowing up on "{subject[:40]}..."\n\nBest regards'

        answer += f"\n{_format_email(doc)}"
        answer += f'\n  → Draft: "{draft[:60]}..."\n'

    # Could create actions for drafting replies
    actions = [
        {
            "action": "draft_reply",
            "email_id": d["id"],
            "params": {"template": "follow_up", "recipient": d.get("sender")},
        }
        for d in to_follow_up
    ]

    return (answer, actions)
