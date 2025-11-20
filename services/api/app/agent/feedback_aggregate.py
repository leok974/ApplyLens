"""
Agent V2 Feedback Aggregation

Aggregates user feedback from agent_feedback table into agent_preferences table.
This creates the learning loop: user feedback → preferences → filtered results.

Usage:
    # Aggregate for a single user
    await aggregate_feedback_for_user(db, user_id)

    # Aggregate for all users (nightly job)
    await aggregate_feedback_for_all_users(db)
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
import logging

from app.models import AgentFeedback, AgentPreferences

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 90


def aggregate_feedback_for_user(db: Session, user_id: str) -> int:
    """
    Build preferences for a single user and upsert into AgentPreferences.

    Args:
        db: Database session
        user_id: User ID to aggregate feedback for

    Returns:
        Number of feedback rows processed for this user
    """
    cutoff = datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)

    rows = (
        db.execute(
            select(AgentFeedback).where(
                AgentFeedback.user_id == user_id,
                AgentFeedback.created_at >= cutoff,
            )
        )
        .scalars()
        .all()
    )

    prefs_data = build_prefs_from_rows(rows)

    existing = (
        db.execute(select(AgentPreferences).where(AgentPreferences.user_id == user_id))
        .scalars()
        .first()
    )

    if existing is None:
        existing = AgentPreferences(user_id=user_id, data=prefs_data)
        db.add(existing)
    else:
        existing.data = prefs_data
        existing.updated_at = datetime.utcnow()

    db.commit()
    return len(rows)


def build_prefs_from_rows(rows: List[AgentFeedback]) -> Dict[str, Any]:
    """
    Convert raw AgentFeedback rows into per-intent preferences.
    This is pure python with no DB operations.

    Args:
        rows: List of AgentFeedback objects

    Returns:
        Preferences dict with blocked/done/hidden thread IDs per intent
    """
    prefs = {
        "suspicious": {"blocked_thread_ids": []},
        "followups": {"done_thread_ids": [], "hidden_thread_ids": []},
        "bills": {"autopay_thread_ids": []},
    }

    for r in rows:
        # Suspicious: hide/not_helpful => block thread
        if r.intent == "suspicious" and r.thread_id:
            if r.label in ("not_helpful", "hide"):
                prefs["suspicious"]["blocked_thread_ids"].append(r.thread_id)

        # Followups: done/hide => mark done or hidden
        if r.intent == "followups" and r.thread_id:
            if r.label == "done":
                prefs["followups"]["done_thread_ids"].append(r.thread_id)
            elif r.label == "hide":
                prefs["followups"]["hidden_thread_ids"].append(r.thread_id)

        # Bills: done => treat as autopay/ignore
        if r.intent == "bills" and r.thread_id:
            if r.label == "done":
                prefs["bills"]["autopay_thread_ids"].append(r.thread_id)

    # De-dup and sort for determinism
    for intent in prefs:
        for key in prefs[intent]:
            prefs[intent][key] = sorted(set(prefs[intent][key]))

    return prefs


def aggregate_feedback_for_all_users(db: Session) -> Dict[str, int]:
    """
    Entry point used by the route / cron.
    Aggregates feedback for all users and returns JSON-safe stats.

    Args:
        db: Database session

    Returns:
        Stats dict with user_count and total_feedback_rows (ints only, no NaN/Infinity)
    """
    # Distinct users who have left any feedback at all
    user_ids = db.execute(select(AgentFeedback.user_id).distinct()).scalars().all()

    if not user_ids:
        return {"user_count": 0, "total_feedback_rows": 0}

    total_rows = db.execute(
        select(func.count()).select_from(AgentFeedback)
    ).scalar_one()

    # Loop per user to populate AgentPreferences
    processed_users = 0
    for uid in user_ids:
        try:
            aggregate_feedback_for_user(db, uid)
            processed_users += 1
        except Exception as e:
            logger.error(f"Failed to aggregate feedback for user {uid}: {e}")
            continue

    logger.info(
        f"Aggregated feedback for {processed_users} users "
        f"({total_rows} total feedback rows)"
    )

    return {
        "user_count": processed_users,
        "total_feedback_rows": int(total_rows),
    }
