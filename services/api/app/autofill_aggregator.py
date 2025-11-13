"""
Autofill event aggregation for learning loop.

Aggregates AutofillEvent rows into FormProfile statistics:
- Canonical field mappings (most common selector->semantic pairs)
- Success rate (% of events with status='ok')
- Average edit distance (chars added/deleted)
- Average completion time

Run via cron or CLI to periodically update profiles.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

from sqlalchemy.orm import Session

from .db import SessionLocal
from .models_learning_db import AutofillEvent, FormProfile, GenStyle

logger = logging.getLogger(__name__)


def _compute_canonical_map(events: List[AutofillEvent]) -> Dict[str, str]:
    """
    Build canonical selector->semantic mapping.

    We look at final_map for each event, count (selector, semantic) pairs,
    and pick the most common semantic for each selector.

    Example:
        Event 1: {"input[name='first']": "first_name"}
        Event 2: {"input[name='first']": "first_name"}
        Event 3: {"input[name='first']": "given_name"}
        Result: {"input[name='first']": "first_name"}  # 2 votes wins
    """
    counts: Dict[str, Counter] = defaultdict(Counter)

    for ev in events:
        final_map = ev.final_map or {}
        for selector, semantic in final_map.items():
            if not semantic:
                continue
            counts[selector][semantic] += 1

    canonical: Dict[str, str] = {}
    for selector, c in counts.items():
        if not c:
            continue
        # Pick semantic with highest count; ties resolved arbitrarily
        semantic, _ = c.most_common(1)[0]
        canonical[selector] = semantic

    return canonical


def _compute_stats(events: List[AutofillEvent]) -> Tuple[float, float, int]:
    """
    Returns (success_rate, avg_edit_chars, avg_duration_ms).

    Success rate: % of events with status='ok'
    Avg edit chars: Average total characters changed (added + deleted)
    Avg duration: Average milliseconds from autofill to completion
    """
    if not events:
        return 0.0, 0.0, 0

    total = len(events)
    success = sum(1 for ev in events if ev.status == "ok")

    total_edit_chars = 0
    total_duration = 0

    for ev in events:
        edit_stats = ev.edit_stats or {}
        total_edit_chars += int(edit_stats.get("total_chars_added", 0)) + int(
            edit_stats.get("total_chars_deleted", 0)
        )
        total_duration += int(ev.duration_ms or 0)

    success_rate = success / total
    avg_edit_chars = total_edit_chars / total
    avg_duration_ms = int(total_duration / total)

    return success_rate, avg_edit_chars, avg_duration_ms


def _update_gen_style_weights(db: Session, host: str, schema_hash: str) -> None:
    """
    Optional simple style ranking per host/schema.

    Computes reward ~ inverse edit_chars and bumps prior_weight.
    Lower edit distance = better style = higher weight.

    This is a simple heuristic; Phase 3.0 will use proper A/B testing.
    """
    # Group events by gen_style_id and compute avg edit chars
    # Note: This is simplified - works on both SQLite and PostgreSQL
    events = (
        db.query(AutofillEvent)
        .filter(
            AutofillEvent.host == host,
            AutofillEvent.schema_hash == schema_hash,
            AutofillEvent.gen_style_id.isnot(None),
        )
        .all()
    )

    # Group by style and calculate averages
    style_stats: Dict[str, List[float]] = defaultdict(list)
    for ev in events:
        edit_stats = ev.edit_stats or {}
        total_edits = int(edit_stats.get("total_chars_added", 0)) + int(
            edit_stats.get("total_chars_deleted", 0)
        )
        style_stats[ev.gen_style_id].append(float(total_edits))

    for gen_style_id, edit_list in style_stats.items():
        if not edit_list:
            continue

        style = db.query(GenStyle).filter(GenStyle.id == gen_style_id).first()
        if not style:
            continue

        avg_edit_chars = sum(edit_list) / len(edit_list)

        # Crude heuristic: lower edits → higher weight
        # Reward = 1 / (1 + avg_edits), multiply weight by (1 + reward * 0.1)
        reward = 1.0 / (1.0 + avg_edit_chars)
        style.prior_weight = float(style.prior_weight or 1.0) * (1.0 + reward * 0.1)

    db.flush()


def aggregate_autofill_profiles(db: Session, *, days: int = 30) -> int:
    """
    Aggregate AutofillEvent into FormProfile for last N days.

    For each unique (host, schema_hash) pair:
    1. Load all events
    2. Compute canonical field mappings
    3. Compute success_rate, avg_edit_chars, avg_duration_ms
    4. Upsert FormProfile
    5. Update GenStyle weights

    Args:
        db: Database session
        days: Look back N days (0 = all events)

    Returns:
        Number of profiles updated
    """
    # Get distinct (host, schema_hash) pairs
    query = db.query(
        AutofillEvent.host,
        AutofillEvent.schema_hash,
    ).distinct()

    # Filter by date if days > 0
    if days > 0:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.filter(AutofillEvent.created_at >= cutoff)

    pairs = query.all()
    updated = 0

    for host, schema_hash in pairs:
        # Load all events for this form
        events_query = db.query(AutofillEvent).filter(
            AutofillEvent.host == host,
            AutofillEvent.schema_hash == schema_hash,
        )

        if days > 0:
            cutoff = datetime.utcnow() - timedelta(days=days)
            events_query = events_query.filter(AutofillEvent.created_at >= cutoff)

        events = events_query.all()

        if not events:
            continue

        # Compute aggregates
        canonical_map = _compute_canonical_map(events)
        success_rate, avg_edit_chars, avg_duration_ms = _compute_stats(events)

        # Upsert profile
        profile = (
            db.query(FormProfile)
            .filter(
                FormProfile.host == host,
                FormProfile.schema_hash == schema_hash,
            )
            .first()
        )

        if not profile:
            profile = FormProfile(
                host=host,
                schema_hash=schema_hash,
            )
            db.add(profile)

        profile.fields = canonical_map
        profile.success_rate = success_rate
        profile.avg_edit_chars = avg_edit_chars
        profile.avg_duration_ms = avg_duration_ms
        profile.last_seen_at = datetime.utcnow()

        # Update style weights
        _update_gen_style_weights(db, host, schema_hash)

        updated += 1
        logger.info(
            f"Updated profile for {host}/{schema_hash}: "
            f"{len(canonical_map)} fields, {success_rate:.1%} success, "
            f"{avg_edit_chars:.1f} avg edits"
        )

    return updated


def run_aggregator(days: int = 30) -> int:
    """
    Entry point for CLI / cron container.

    Opens a database session, runs aggregation, commits changes.

    Usage:
        python -c "from app.autofill_aggregator import run_aggregator; print(run_aggregator(days=30))"
    """
    db = SessionLocal()
    try:
        updated = aggregate_autofill_profiles(db, days=days)
        db.commit()
        logger.info(f"Aggregation complete: {updated} profiles updated")
        return updated
    except Exception as e:
        db.rollback()
        logger.error(f"Aggregation failed: {e}")
        raise
    finally:
        db.close()
