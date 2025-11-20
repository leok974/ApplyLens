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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
import logging

from app.models import AgentFeedback, AgentPreferences

logger = logging.getLogger(__name__)


async def aggregate_feedback_for_user(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    """
    Aggregate feedback for a single user and update preferences.

    Logic:
    - Look at last 90 days of feedback
    - Build preferences from feedback labels:
        - suspicious: hide/not_helpful → blocked_thread_ids
        - followups: done → done_thread_ids, hide → hidden_thread_ids
        - bills: done → autopay_thread_ids
    - Upsert to agent_preferences table

    Returns: The aggregated preferences dict
    """
    cutoff = datetime.utcnow() - timedelta(days=90)

    # Load recent feedback for this user
    result = await db.execute(
        select(AgentFeedback)
        .where(AgentFeedback.user_id == user_id)
        .where(AgentFeedback.created_at >= cutoff)
        .order_by(AgentFeedback.created_at.desc())
    )
    rows = result.scalars().all()

    if not rows:
        logger.info(f"No feedback found for user {user_id} in last 90 days")
        return {}

    # Build preferences from feedback rows
    prefs = build_prefs_from_rows(rows)

    # Upsert to agent_preferences
    await upsert_agent_prefs(db, user_id, prefs)

    logger.info(
        f"Aggregated {len(rows)} feedback rows for user {user_id}: "
        f"{len(prefs.get('suspicious', {}).get('blocked_thread_ids', []))} suspicious blocked, "
        f"{len(prefs.get('followups', {}).get('done_thread_ids', []))} followups done, "
        f"{len(prefs.get('bills', {}).get('autopay_thread_ids', []))} bills on autopay"
    )

    return prefs


def build_prefs_from_rows(rows: List[AgentFeedback]) -> Dict[str, Any]:
    """
    Build preferences dict from feedback rows.

    Aggregation rules:
    - suspicious + (not_helpful OR hide) → blocked_thread_ids
    - followups + done → done_thread_ids
    - followups + hide → hidden_thread_ids
    - bills + done → autopay_thread_ids

    Returns: Dict like:
    {
        "suspicious": {"blocked_thread_ids": ["thread-1", "thread-2"]},
        "followups": {"done_thread_ids": [...], "hidden_thread_ids": [...]},
        "bills": {"autopay_thread_ids": [...]}
    }
    """
    prefs = {
        "suspicious": {"blocked_thread_ids": []},
        "followups": {"done_thread_ids": [], "hidden_thread_ids": []},
        "bills": {"autopay_thread_ids": []},
    }

    for row in rows:
        # Skip if no thread_id (can't filter without it)
        if not row.thread_id:
            continue

        # Suspicious intent: hide or not_helpful → block
        if row.intent == "suspicious" and row.label in ("not_helpful", "hide"):
            prefs["suspicious"]["blocked_thread_ids"].append(row.thread_id)

        # Followups intent: done → done, hide → hidden
        elif row.intent == "followups":
            if row.label == "done":
                prefs["followups"]["done_thread_ids"].append(row.thread_id)
            elif row.label == "hide":
                prefs["followups"]["hidden_thread_ids"].append(row.thread_id)

        # Bills intent: done → autopay (user marked as handled/auto-paid)
        elif row.intent == "bills" and row.label == "done":
            prefs["bills"]["autopay_thread_ids"].append(row.thread_id)

    # De-duplicate and sort for consistency
    for intent in prefs:
        for key in prefs[intent]:
            prefs[intent][key] = sorted(set(prefs[intent][key]))

    return prefs


async def upsert_agent_prefs(
    db: AsyncSession, user_id: str, prefs: Dict[str, Any]
) -> None:
    """
    Upsert preferences to agent_preferences table.

    Uses PostgreSQL INSERT ... ON CONFLICT to update if exists.
    """
    stmt = insert(AgentPreferences).values(
        user_id=user_id,
        data=prefs,
        updated_at=datetime.utcnow(),
    )

    # On conflict (user_id already exists), update data and updated_at
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id"],
        set_={
            "data": prefs,
            "updated_at": datetime.utcnow(),
        },
    )

    await db.execute(stmt)
    await db.commit()


async def aggregate_feedback_for_all_users(db: AsyncSession) -> Dict[str, int]:
    """
    Aggregate feedback for all users who have feedback.

    This is the nightly job entry point.

    Returns: Stats dict with user_count and total_feedback_rows
    """
    # Find all users with recent feedback
    cutoff = datetime.utcnow() - timedelta(days=90)

    result = await db.execute(
        select(AgentFeedback.user_id, func.count(AgentFeedback.id).label("count"))
        .where(AgentFeedback.created_at >= cutoff)
        .group_by(AgentFeedback.user_id)
    )
    user_counts = result.all()

    total_feedback_rows = 0
    processed_users = 0

    for user_id, count in user_counts:
        try:
            await aggregate_feedback_for_user(db, user_id)
            processed_users += 1
            total_feedback_rows += count
        except Exception as e:
            logger.error(f"Failed to aggregate feedback for user {user_id}: {e}")
            continue

    logger.info(
        f"Aggregated feedback for {processed_users} users "
        f"({total_feedback_rows} total feedback rows)"
    )

    return {
        "user_count": processed_users,
        "total_feedback_rows": total_feedback_rows,
    }
