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

from ..deps.user import get_current_user_email
from ..es import ES_ENABLED, INDEX, es

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


# ===== Endpoints =====


@router.get("/inbox")
async def get_inbox_actions(
    user_email: str = Depends(get_current_user_email),
) -> List[ActionRow]:
    """
    Get actionable emails that need cleanup/attention.

    Returns emails flagged as promotions, bulk, risky, or unread.
    """
    try:
        if not ES_ENABLED or es is None:
            logger.info("Inbox actions: ES disabled, returning empty list")
            return []

        # Query ES for actionable emails
        body = {
            "size": 50,
            "query": {
                "bool": {
                    "must": [{"term": {"owner_email.keyword": user_email}}],
                    "should": [
                        {"term": {"labels": "PROMOTIONS"}},
                        {"term": {"labels": "CATEGORY_PROMOTIONS"}},
                        {"term": {"labels": "UNREAD"}},
                        {"range": {"risk_score": {"gte": 50}}},
                        {"term": {"quarantined": True}},
                    ],
                    "minimum_should_match": 1,
                }
            },
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

            # Build reason
            risk_score = src.get("risk_score")
            quarantined = src.get("quarantined", False)
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
                subject=src.get("subject", ""),
                received_at=src.get("received_at", ""),
                labels=labels,
                reason=reason,
                allowed_actions=allowed_actions,
            )
            rows.append(row)

        logger.info(
            f"Inbox actions: Found {len(rows)} actionable emails for {user_email}"
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

    Returns a human-readable summary based on email metadata.
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

        # Build explanation
        category = categorize_email(labels, risk_score, quarantined)
        signals = build_signals(category, labels, risk_score, src.get("sender"))

        # Create summary
        summary_parts = [
            f"This email is categorized as {category}",
            "because it " + " and ".join(signals[:2]).lower(),
        ]

        if risk_score:
            risk_level = (
                "low" if risk_score < 30 else "medium" if risk_score < 70 else "high"
            )
            summary_parts.append(f"Risk score is {risk_level} ({int(risk_score)}/100)")

        if quarantined:
            summary_parts.append("and has been quarantined for review")
        else:
            summary_parts.append("so it's likely safe but noisy")

        summary = ", ".join(summary_parts) + "."

        return ExplainResponse(summary=summary)

    except Exception as e:
        logger.exception(f"Explain action failed: {e}")
        return ExplainResponse(summary=f"Error explaining email: {str(e)}")


@router.post("/mark_safe")
async def mark_safe(
    req: ActionRequest,
    user_email: str = Depends(get_current_user_email),
) -> ActionResponse:
    """
    Mark an email as safe (user-approved).

    Updates the email's risk score and clears quarantine flag.
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
                    "source": "ctx._source.risk_score = Math.min(ctx._source.risk_score ?: 100, 10); ctx._source.quarantined = false; ctx._source.user_overrode_safe = true",
                    "lang": "painless",
                }
            },
        )

        logger.info(f"Marked {req.message_id} as safe by {user_email}")
        return ActionResponse(ok=True)

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
        return ActionResponse(ok=True)

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
        return ActionResponse(ok=True)

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

        # Update email - mark as unsubscribed
        es.update(
            index=INDEX,
            id=req.message_id,
            body={
                "script": {
                    "source": "ctx._source.user_unsubscribed = true; ctx._source.unsubscribed_at = params.now",
                    "lang": "painless",
                    "params": {"now": datetime.utcnow().isoformat()},
                }
            },
        )

        # TODO: In future, maintain a list of muted senders per user
        logger.info(f"Unsubscribed from {sender} for {user_email}")
        return ActionResponse(ok=True)

    except Exception as e:
        logger.exception(f"Unsubscribe failed: {e}")
        raise HTTPException(500, f"Failed to unsubscribe: {str(e)}")
