"""
Inbox Actions Router - Quick Actions for Email Management

Endpoints for the /inbox-actions page:
- GET /api/actions/inbox - Get actionable emails
- POST /api/actions/explain - Explain why email needs action
- POST /api/actions/mark_safe - Mark email as safe
- POST /api/actions/mark_suspicious - Mark email as suspicious
- POST /api/actions/archive - Archive email
- POST /api/actions/unsubscribe - Unsubscribe from sender
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps.user import get_current_user_email
from ..es import ES_ENABLED, INDEX, es
from .senders import get_overrides_for_user, upsert_sender_override_safe

router = APIRouter(prefix="/actions", tags=["inbox_actions"])
logger = logging.getLogger(__name__)

# Check if mutations are allowed in this environment
ALLOW_ACTION_MUTATIONS = os.getenv("ALLOW_ACTION_MUTATIONS", "true").lower() == "true"


# ===== Models =====


class ActionRow(BaseModel):
    """Email row for inbox actions page."""

    message_id: str
    from_name: str
    from_email: str
    subject: str
    received_at: str
    labels: List[str]
    reason: Dict[str, Any]
    allowed_actions: List[str]
    # Lifecycle flags for UI
    archived: bool = False
    quarantined: bool = False
    muted: bool = False
    user_overrode_safe: bool = False
    # Actionability signals
    risk_score: int = 0
    unread: bool = True


class ExplainRequest(BaseModel):
    """Request to explain why an email needs action."""

    message_id: str


class ExplainResponse(BaseModel):
    """Response with explanation."""

    summary: str


class ActionRequest(BaseModel):
    """Request to perform an action on an email."""

    message_id: str


class ActionResponse(BaseModel):
    """Response from action."""

    ok: bool
    message_id: Optional[str] = None
    new_risk_score: Optional[int] = None
    quarantined: Optional[bool] = None
    archived: Optional[bool] = None
    muted: Optional[bool] = None
    user_overrode_safe: Optional[bool] = None


class MessageDetailResponse(BaseModel):
    """Full message detail for drawer view."""

    message_id: str
    from_name: Optional[str] = None
    from_email: Optional[str] = None
    to_email: Optional[str] = None
    subject: str
    received_at: str
    risk_score: Optional[int] = None
    quarantined: Optional[bool] = None
    category: Optional[str] = None
    html_body: Optional[str] = None
    text_body: Optional[str] = None


# ===== Helper Functions =====


def build_allowed_actions() -> List[str]:
    """
    Build list of allowed actions based on ALLOW_ACTION_MUTATIONS env var.

    When ALLOW_ACTION_MUTATIONS=true (dev/local):
        Returns all actions: archive, mark_safe, mark_suspicious, unsubscribe, explain
    When ALLOW_ACTION_MUTATIONS=false (production default):
        Returns only: ["explain"]

    This prevents UI from showing buttons that will 403 in production.
    """
    if ALLOW_ACTION_MUTATIONS:
        return ["archive", "mark_safe", "mark_suspicious", "unsubscribe", "explain"]
    return ["explain"]


def categorize_email(
    labels: List[str], risk_score: Optional[float], quarantined: bool
) -> str:
    """Categorize email based on labels and risk."""
    labels_lower = [label.lower() for label in labels]

    if quarantined or (risk_score and risk_score >= 80):
        return "Suspicious"
    elif "category_promotions" in labels_lower or "promotions" in labels_lower:
        return "Promotions"
    elif "category_updates" in labels_lower:
        return "Updates"
    elif "category_forums" in labels_lower:
        return "Forums"
    elif "spam" in labels_lower:
        return "Spam"
    elif "unread" in labels_lower:
        return "Unread"
    return "Other"


def build_signals(
    category: str,
    labels: List[str],
    risk_score: Optional[float],
    sender: Optional[str],
) -> List[str]:
    """Build list of signals explaining why email needs action."""
    signals = []

    # Label-based signals
    if "promotions" in [label.lower() for label in labels]:
        signals.append("Labeled PROMOTIONS by Gmail")

    if category == "Promotions":
        signals.append("Newsletter / marketing keywords")

    if "unread" in [label.lower() for label in labels]:
        signals.append("Unread email")

    # Risk-based signals
    if risk_score and risk_score > 50:
        signals.append(f"Risk score: {int(risk_score)}/100")

    if risk_score and risk_score < 20:
        signals.append("Low risk sender")

    # Sender-based signals
    if sender and "noreply" in sender.lower():
        signals.append("Automated sender (no-reply)")

    if not signals:
        signals.append("Matches bulk email pattern")

    return signals


def generate_explanation_for_message(
    category: str,
    signals: List[str],
    risk_score: int,
    quarantined: bool,
) -> str:
    """
    Generate a human-readable explanation for why an email needs action.

    Uses deterministic heuristics based on category, signals, risk_score, and quarantined status.
    No LLM calls - purely rule-based.

    Args:
        category: Email category (Promotions, Updates, Suspicious, etc.)
        signals: List of signal strings explaining why it was flagged
        risk_score: Risk score 0-100
        quarantined: Whether email is quarantined

    Returns:
        A 2-4 sentence human-readable explanation
    """
    # Determine base explanation based on category
    cat_lower = category.lower()
    if "promo" in cat_lower or cat_lower == "promotions":
        base = "This looks like marketing or promotional content."
    elif cat_lower == "updates":
        base = "This looks like an automated update or notification."
    elif cat_lower == "suspicious" or cat_lower == "spam":
        base = "This email was flagged as potentially suspicious."
    elif cat_lower == "forums":
        base = "This appears to be a forum or community notification."
    else:
        base = f"This email was categorized as {category}."

    # Determine risk state
    if risk_score >= 80 or quarantined:
        safe_state = "high risk"
    elif risk_score >= 50:
        safe_state = "medium risk"
    else:
        safe_state = "low risk"

    # Build signals text (take first 3)
    signals_text = "; ".join(signals[:3]) if signals else "internal signals"

    # Build action hints
    action_hint = []
    if quarantined:
        action_hint.append("Treat with caution.")
    elif "promo" in cat_lower or cat_lower in ("promotions", "updates"):
        action_hint.append("You can safely archive it if it's not relevant.")
    else:
        action_hint.append("Review before taking action.")

    return (
        f"{base} It was flagged because: {signals_text}. "
        f"Risk is {safe_state} (score {risk_score}/100). " + " ".join(action_hint)
    )


# ===== Endpoints =====


@router.get("/inbox")
async def get_inbox_actions(
    mode: str = "review",
    user_email: str = Depends(get_current_user_email),
) -> List[ActionRow]:
    """
    Get actionable emails that need cleanup/attention.

    Args:
        mode: Filter mode - "review" (default), "quarantined", or "archived"
        user_email: Current user's email

    Returns:
        - review: Emails needing triage (not archived/muted/safe, excluding quarantined)
        - quarantined: Emails marked suspicious or high-risk
        - archived: Emails user has handled (archived/safe/muted)
    """
    try:
        if not ES_ENABLED or es is None:
            logger.info("Inbox actions: ES disabled, returning empty list")
            return []

        # Build query based on mode
        must_clauses = [{"term": {"owner_email.keyword": user_email}}]
        must_not_clauses = []
        should_clauses = []

        if mode == "quarantined":
            # Show only quarantined emails
            must_clauses.append({"term": {"quarantined": True}})
        elif mode == "archived":
            # Show archived, safe, or muted emails
            should_clauses = [
                {"term": {"user_archived": True}},
                {"term": {"user_overrode_safe": True}},
                {"term": {"user_unsubscribed": True}},
            ]
        else:  # mode == "review" (default)
            # Show emails that need review: not handled yet, and either unread OR risky
            # Exclude items that have been explicitly handled
            must_not_clauses = [
                {"term": {"user_archived": True}},
                {"term": {"user_overrode_safe": True}},
                {"term": {"user_unsubscribed": True}},
                {"term": {"quarantined": True}},
            ]
            # Much looser criteria: unread OR risk >= 40
            # This will be further filtered in Python after fetching
            should_clauses = [
                {"term": {"labels": "UNREAD"}},
                {"range": {"risk_score": {"gte": 40}}},
                {"term": {"labels": "PROMOTIONS"}},
                {"term": {"labels": "CATEGORY_PROMOTIONS"}},
            ]

        query_body = {"must": must_clauses}
        if must_not_clauses:
            query_body["must_not"] = must_not_clauses
        if should_clauses:
            query_body["should"] = should_clauses
            query_body["minimum_should_match"] = 1

        # Query ES for actionable emails
        body = {
            "size": 50,
            "query": {"bool": query_body},
            "sort": [{"received_at": {"order": "desc"}}],
            "_source": [
                "gmail_id",
                "id",
                "sender",
                "subject",
                "received_at",
                "labels",
                "risk_score",
                "quarantined",
                "label_heuristics",
                "user_archived",
                "user_overrode_safe",
                "user_unsubscribed",
            ],
        }

        result = es.search(index=INDEX, body=body)
        hits = result.get("hits", {}).get("hits", [])

        rows = []
        for hit in hits:
            src = hit.get("_source", {})

            # Extract message ID
            message_id = src.get("gmail_id") or src.get("id") or hit.get("_id", "")

            # Extract sender info
            sender = src.get("sender", "")
            from_name = sender.split("<")[0].strip() if "<" in sender else sender
            from_email = sender.split("<")[1].split(">")[0] if "<" in sender else sender

            # Get labels
            labels = src.get("labels", [])

            # Extract lifecycle flags with proper defaults
            risk_score = src.get("risk_score", 0)
            if risk_score is None:
                risk_score = 0

            # Check if unread - default to True if missing (assume new/unseen)
            unread = "UNREAD" in labels or src.get("unread", True)
            if unread is None:
                unread = True

            # Lifecycle flags
            archived = src.get("user_archived", False) or src.get("archived", False)
            quarantined = src.get("quarantined", False)
            muted = src.get("user_unsubscribed", False) or src.get("muted", False)
            user_overrode_safe = src.get("user_overrode_safe", False) or src.get(
                "marked_safe", False
            )

            # For review mode, apply Python-side filtering
            if mode == "review":
                # Skip if user already handled this
                already_handled = archived or muted or user_overrode_safe or quarantined
                if already_handled:
                    continue

                # Must be unread OR risky (>= 40)
                is_actionable = unread or risk_score >= 40
                if not is_actionable:
                    continue

            # Build reason
            category = categorize_email(labels, risk_score, quarantined)
            signals = build_signals(category, labels, risk_score, sender)

            reason = {
                "category": category,
                "signals": signals,
                "risk_score": int(risk_score) if risk_score else 0,
                "quarantined": quarantined,
            }

            # Build allowed actions based on ALLOW_ACTION_MUTATIONS env var
            allowed_actions = build_allowed_actions()

            row = ActionRow(
                message_id=str(message_id),
                from_name=from_name,
                from_email=from_email,
                subject=src.get("subject", "(no subject)"),
                received_at=src.get("received_at", ""),
                labels=labels,
                reason=reason,
                allowed_actions=allowed_actions,
                # Lifecycle flags
                archived=archived,
                quarantined=quarantined,
                muted=muted,
                user_overrode_safe=user_overrode_safe,
                # Actionability signals
                risk_score=int(risk_score),
                unread=unread,
            )
            rows.append(row)

        logger.info(
            f"Inbox actions [{mode}]: Found {len(rows)} actionable emails for {user_email}"
        )
        return rows

    except Exception as e:
        logger.exception(f"Inbox actions failed for user {user_email}: {e}")
        return []


@router.post("/explain")
async def explain_action(
    req: ExplainRequest,
    user_email: str = Depends(get_current_user_email),
) -> ExplainResponse:
    """
    Explain why an email needs action.

    Returns a human-readable summary based on email metadata using deterministic heuristics.
    """
    try:
        if not ES_ENABLED or es is None:
            return ExplainResponse(
                summary="Unable to explain: search service unavailable"
            )

        # Fetch email from ES
        result = es.search(
            index=INDEX,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"owner_email.keyword": user_email}},
                            {"term": {"gmail_id": req.message_id}},
                        ]
                    }
                },
                "size": 1,
                "_source": [
                    "labels",
                    "risk_score",
                    "quarantined",
                    "sender",
                    "label_heuristics",
                ],
            },
        )

        hits = result.get("hits", {}).get("hits", [])
        if not hits:
            return ExplainResponse(summary="Email not found")

        src = hits[0].get("_source", {})
        labels = src.get("labels", [])
        risk_score = src.get("risk_score", 0)
        quarantined = src.get("quarantined", False)

        # Build explanation using our helper
        category = categorize_email(labels, risk_score, quarantined)
        signals = build_signals(category, labels, risk_score, src.get("sender"))
        summary = generate_explanation_for_message(
            category=category,
            signals=signals,
            risk_score=int(risk_score) if risk_score else 0,
            quarantined=quarantined,
        )

        return ExplainResponse(summary=summary)

    except Exception as e:
        logger.exception(f"Explain action failed: {e}")
        return ExplainResponse(summary=f"Error explaining email: {str(e)}")


@router.get("/message/{message_id}")
async def get_message_detail(
    message_id: str,
    user_email: str = Depends(get_current_user_email),
) -> MessageDetailResponse:
    """
    Get full message detail for drawer view.

    Returns complete email information including body (HTML/text) for display.
    """
    try:
        if not ES_ENABLED or es is None:
            raise HTTPException(status_code=503, detail="Search service unavailable")

        # Fetch full email from ES
        result = es.search(
            index=INDEX,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"owner_email.keyword": user_email}},
                            {"term": {"gmail_id": message_id}},
                        ]
                    }
                },
                "size": 1,
                "_source": [
                    "gmail_id",
                    "id",
                    "sender",
                    "recipient",
                    "subject",
                    "received_at",
                    "labels",
                    "risk_score",
                    "quarantined",
                    "body_html",
                    "body_text",
                    "body",
                ],
            },
        )

        hits = result.get("hits", {}).get("hits", [])
        if not hits:
            raise HTTPException(status_code=404, detail="Message not found")

        src = hits[0].get("_source", {})

        # Extract sender info
        sender = src.get("sender", "")
        from_name = sender.split("<")[0].strip() if "<" in sender else sender
        from_email = sender.split("<")[1].split(">")[0] if "<" in sender else sender

        # Extract body (try different field names)
        html_body = src.get("body_html") or src.get("body")
        text_body = src.get("body_text") or src.get("body")

        # If we have HTML, clear text_body to avoid duplication
        if html_body and text_body == html_body:
            text_body = None

        # Build categorization for context
        labels = src.get("labels", [])
        risk_score = src.get("risk_score")
        quarantined = src.get("quarantined", False)
        category = categorize_email(labels, risk_score, quarantined)

        return MessageDetailResponse(
            message_id=message_id,
            from_name=from_name if from_name != from_email else None,
            from_email=from_email,
            to_email=src.get("recipient"),
            subject=src.get("subject", ""),
            received_at=src.get("received_at", ""),
            risk_score=int(risk_score) if risk_score is not None else None,
            quarantined=quarantined,
            category=category,
            html_body=html_body,
            text_body=text_body,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Get message detail failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get message: {str(e)}")


@router.post("/mark_safe")
async def mark_safe(
    req: ActionRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> ActionResponse:
    """
    Mark an email as safe (user-approved).

    Updates the email's risk score, clears quarantine, and marks as archived.
    Safe emails go to the Archived view.

    Also records a sender-level override in Postgres so future emails from
    this sender are trusted and won't clutter Needs Review (adaptive classification).
    """
    if not ALLOW_ACTION_MUTATIONS:
        raise HTTPException(403, "Actions are read-only in production")

    try:
        if not ES_ENABLED or es is None:
            raise HTTPException(503, "Search service unavailable")

        # Get the email to extract sender
        msg = es.get(index=INDEX, id=req.message_id)
        sender_email = msg["_source"].get("from_email") or msg["_source"].get("sender")

        # Update email in ES
        es.update(
            index=INDEX,
            id=req.message_id,
            body={
                "script": {
                    "source": """
                        ctx._source.risk_score = 5;
                        ctx._source.quarantined = false;
                        ctx._source.user_overrode_safe = true;
                        if (ctx._source.labels == null) { ctx._source.labels = [] }
                        if (!ctx._source.labels.contains('ARCHIVED')) { ctx._source.labels.add('ARCHIVED') }
                    """,
                    "lang": "painless",
                }
            },
        )

        # Record sender-level override for adaptive classification
        if sender_email:
            upsert_sender_override_safe(db, user_email, sender_email)
            logger.info(f"Recorded safe override for sender {sender_email}")

        logger.info(f"Marked {req.message_id} as safe by {user_email}")
        return ActionResponse(
            ok=True,
            message_id=req.message_id,
            new_risk_score=5,
            quarantined=False,
            archived=True,
            user_overrode_safe=True,
        )

    except Exception as e:
        logger.exception(f"Mark safe failed: {e}")
        raise HTTPException(500, f"Failed to mark safe: {str(e)}")


@router.post("/mark_suspicious")
async def mark_suspicious(
    req: ActionRequest,
    user_email: str = Depends(get_current_user_email),
) -> ActionResponse:
    """
    Mark an email as suspicious (user-flagged).

    Raises risk score and sets quarantine flag.
    """
    if not ALLOW_ACTION_MUTATIONS:
        raise HTTPException(403, "Actions are read-only in production")

    try:
        if not ES_ENABLED or es is None:
            raise HTTPException(503, "Search service unavailable")

        # Update email in ES
        es.update(
            index=INDEX,
            id=req.message_id,
            body={
                "script": {
                    "source": "ctx._source.risk_score = 95; ctx._source.quarantined = true; ctx._source.user_flagged_suspicious = true",
                    "lang": "painless",
                }
            },
        )

        logger.info(f"Marked {req.message_id} as suspicious by {user_email}")
        return ActionResponse(
            ok=True,
            message_id=req.message_id,
            new_risk_score=95,
            quarantined=True,
        )

    except Exception as e:
        logger.exception(f"Mark suspicious failed: {e}")
        raise HTTPException(500, f"Failed to mark suspicious: {str(e)}")


@router.post("/archive")
async def archive_email(
    req: ActionRequest,
    user_email: str = Depends(get_current_user_email),
) -> ActionResponse:
    """
    Archive an email (hide from inbox).

    Marks the email as archived in our local mirror.
    """
    if not ALLOW_ACTION_MUTATIONS:
        raise HTTPException(403, "Actions are read-only in production")

    try:
        if not ES_ENABLED or es is None:
            raise HTTPException(503, "Search service unavailable")

        # Update email in ES - add archived flag
        es.update(
            index=INDEX,
            id=req.message_id,
            body={
                "script": {
                    "source": "if (ctx._source.labels == null) { ctx._source.labels = [] } if (!ctx._source.labels.contains('ARCHIVED')) { ctx._source.labels.add('ARCHIVED') } ctx._source.user_archived = true",
                    "lang": "painless",
                }
            },
        )

        logger.info(f"Archived {req.message_id} by {user_email}")
        return ActionResponse(
            ok=True,
            message_id=req.message_id,
            archived=True,
        )

    except Exception as e:
        logger.exception(f"Archive failed: {e}")
        raise HTTPException(500, f"Failed to archive: {str(e)}")


@router.post("/unsubscribe")
async def unsubscribe(
    req: ActionRequest,
    user_email: str = Depends(get_current_user_email),
) -> ActionResponse:
    """
    Unsubscribe from sender (mark as muted).

    Marks the email as muted/unsubscribed and archives it.
    For now, just marks sender as unsubscribed in our DB.
    Doesn't actually click unsubscribe links yet.
    """
    if not ALLOW_ACTION_MUTATIONS:
        raise HTTPException(403, "Actions are read-only in production")

    try:
        if not ES_ENABLED or es is None:
            raise HTTPException(503, "Search service unavailable")

        # Get email to extract sender
        result = es.get(index=INDEX, id=req.message_id, _source=["sender"])
        sender = result.get("_source", {}).get("sender", "")

        if not sender:
            raise HTTPException(400, "Cannot unsubscribe: no sender found")

        # Update email - mark as unsubscribed and archived
        es.update(
            index=INDEX,
            id=req.message_id,
            body={
                "script": {
                    "source": """
                        ctx._source.user_unsubscribed = true;
                        ctx._source.unsubscribed_at = params.now;
                        if (ctx._source.labels == null) { ctx._source.labels = [] }
                        if (!ctx._source.labels.contains('ARCHIVED')) { ctx._source.labels.add('ARCHIVED') }
                    """,
                    "lang": "painless",
                    "params": {"now": datetime.utcnow().isoformat()},
                }
            },
        )

        # TODO: In future, maintain a list of muted senders per user
        logger.info(f"Unsubscribed from {sender} for {user_email}")
        return ActionResponse(
            ok=True,
            message_id=req.message_id,
            archived=True,
            muted=True,
        )

    except Exception as e:
        logger.exception(f"Unsubscribe failed: {e}")
        raise HTTPException(500, f"Failed to unsubscribe: {str(e)}")


@router.post("/restore")
async def restore_to_review(
    req: ActionRequest,
    user_email: str = Depends(get_current_user_email),
) -> ActionResponse:
    """
    Restore an email back to Needs Review.

    Clears all lifecycle flags so email appears in review mode again.
    Useful for undoing accidental actions.
    """
    if not ALLOW_ACTION_MUTATIONS:
        raise HTTPException(403, "Actions are read-only in production")

    try:
        if not ES_ENABLED or es is None:
            raise HTTPException(503, "Search service unavailable")

        # Clear all lifecycle flags
        es.update(
            index=INDEX,
            id=req.message_id,
            body={
                "script": {
                    "source": """
                        ctx._source.user_archived = false;
                        ctx._source.user_overrode_safe = false;
                        ctx._source.user_unsubscribed = false;
                        ctx._source.quarantined = false;
                        if (ctx._source.labels != null) {
                            ctx._source.labels.removeIf(label -> label == 'ARCHIVED');
                        }
                    """,
                    "lang": "painless",
                }
            },
        )

        logger.info(f"Restored {req.message_id} to review by {user_email}")
        return ActionResponse(
            ok=True,
            message_id=req.message_id,
            archived=False,
            quarantined=False,
        )

    except Exception as e:
        logger.exception(f"Restore failed: {e}")
        raise HTTPException(500, f"Failed to restore: {str(e)}")


# ===== Metrics / Insights =====


class InboxSummary(BaseModel):
    """Summary metrics for inbox actions."""

    archived: int
    quarantined: int
    muted_senders: int
    safe_senders: int


@router.get("/metrics/summary", response_model=InboxSummary)
async def inbox_actions_summary(
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> InboxSummary:
    """
    Return high-level triage stats for this user.

    These values come from Elasticsearch (archived/quarantined counts) and
    Postgres (sender override counts). Provides at-a-glance visibility into
    user's classification behavior.
    """
    try:
        if not ES_ENABLED or es is None:
            # Return zeros if ES unavailable
            return InboxSummary(
                archived=0,
                quarantined=0,
                muted_senders=0,
                safe_senders=0,
            )

        # Count archived emails (user_archived=true OR user_overrode_safe=true OR muted=true)
        archived_query = {
            "query": {
                "bool": {
                    "filter": [{"term": {"owner": user_email}}],
                    "should": [
                        {"term": {"user_archived": True}},
                        {"term": {"user_overrode_safe": True}},
                        {"term": {"muted": True}},
                        {"term": {"user_unsubscribed": True}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            "size": 0,
        }
        archived_resp = es.search(index=INDEX, body=archived_query)
        archived_count = archived_resp["hits"]["total"]["value"]

        # Count quarantined emails
        quarantined_query = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"owner": user_email}},
                        {"term": {"quarantined": True}},
                    ]
                }
            },
            "size": 0,
        }
        quarantined_resp = es.search(index=INDEX, body=quarantined_query)
        quarantined_count = quarantined_resp["hits"]["total"]["value"]

        # Count sender overrides from Postgres
        user_overrides = get_overrides_for_user(db, user_email)
        muted_senders = sum(1 for ov in user_overrides if ov["muted"])
        safe_senders = sum(1 for ov in user_overrides if ov["safe"])

        return InboxSummary(
            archived=archived_count,
            quarantined=quarantined_count,
            muted_senders=muted_senders,
            safe_senders=safe_senders,
        )

    except Exception as e:
        logger.exception(f"Failed to get inbox summary: {e}")
        # Return zeros on error (graceful degradation)
        return InboxSummary(
            archived=0,
            quarantined=0,
            muted_senders=0,
            safe_senders=0,
        )
