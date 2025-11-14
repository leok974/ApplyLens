"""
Autofill event aggregation for learning loop.

Aggregates AutofillEvent rows into FormProfile statistics:
- Canonical field mappings (most common selector->semantic pairs)
- Success rate (% of events with status='ok')
- Average edit distance (chars added/deleted)
- Average completion time
- Phase 5.0: Style performance tracking and preferred_style_id selection

Run via cron or CLI to periodically update profiles.
"""

from collections import Counter as CollectionsCounter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func

from .db import SessionLocal
from .models_learning_db import AutofillEvent, FormProfile, GenStyle
from .core.metrics import Counter as PrometheusCounter

logger = logging.getLogger(__name__)

# Prometheus metrics
autofill_agg_runs_total = PrometheusCounter(
    "applylens_autofill_agg_runs_total",
    "Total autofill aggregator runs",
    ["status"],  # ok, err
)

autofill_profiles_updated_total = PrometheusCounter(
    "applylens_autofill_profiles_updated_total",
    "Total profiles updated by autofill aggregator",
)


# Phase 5.1: Host-family bundles for cross-form generalization
ATS_FAMILIES: Dict[str, Tuple[str, ...]] = {
    "greenhouse": ("greenhouse.io", "boards.greenhouse.io"),
    "lever": ("lever.co",),
    "workday": ("myworkdayjobs.com",),
    "ashby": ("ashbyhq.com",),
    "bamboohr": ("bamboohr.com",),
}

# Minimum samples required for reliable statistics
MIN_FORM_RUNS = 5  # Per-form minimum
MIN_FAMILY_RUNS = 10  # Per-family minimum
MIN_SEGMENT_RUNS = 5  # Per-segment minimum (Phase 5.2)


def get_host_family(host: str) -> Optional[str]:
    """
    Determine which ATS family a host belongs to.

    Args:
        host: Domain name (e.g., "boards.greenhouse.io")

    Returns:
        Family name (e.g., "greenhouse") or None if not recognized

    Example:
        >>> get_host_family("boards.greenhouse.io")
        "greenhouse"
        >>> get_host_family("unknown-ats.com")
        None
    """
    host = (host or "").lower()
    for family, suffixes in ATS_FAMILIES.items():
        if any(host.endswith(suffix) for suffix in suffixes):
            return family
    return None


# Phase 5.2: Segment-aware tuning
def derive_segment_key(job: Optional[dict]) -> Optional[str]:
    """
    Derive a segment key from job information for style tuning.

    Segments allow different style preferences for different role levels
    (e.g., interns prefer bullet points, seniors prefer narratives).

    Args:
        job: Job information dict with title/seniority fields

    Returns:
        Segment key ("intern", "junior", "senior", "default") or None

    Example:
        >>> derive_segment_key({"title": "Senior Software Engineer"})
        "senior"
        >>> derive_segment_key({"title": "Summer Intern - ML"})
        "intern"
        >>> derive_segment_key(None)
        None
    """
    if not job:
        return None

    # Extract title from normalized_title or title field
    title_raw = job.get("normalized_title") or job.get("title")
    if not title_raw:
        return None

    title = title_raw.lower()

    # Simple heuristic - can be extended later with discipline detection
    if "intern" in title or "co-op" in title:
        return "intern"
    elif "junior" in title or "jr" in title or "entry" in title:
        return "junior"
    elif "senior" in title or "sr" in title or "lead" in title or "principal" in title:
        return "senior"
    else:
        return "default"


# Phase 5.0: Style Performance Tracking
@dataclass
class StyleStats:
    """Performance metrics for a generation style."""

    style_id: str
    helpful: int = 0
    unhelpful: int = 0
    total_runs: int = 0
    avg_edit_chars: float = 0.0

    @property
    def helpful_ratio(self) -> float:
        """Percentage of runs marked helpful."""
        if self.total_runs == 0:
            return 0.0
        return self.helpful / self.total_runs


def _compute_style_stats(
    db: Session, lookback_days: int
) -> Dict[Tuple[str, str], Dict[str, StyleStats]]:
    """
    Aggregate AutofillEvent by (host, schema_hash, gen_style_id).

    Returns a dict: {(host, schema_hash): {style_id: StyleStats}}

    Args:
        db: Database session
        lookback_days: Number of days to look back (0 = all time)

    Returns:
        Mapping of (host, schema) to style performance stats
    """
    query = db.query(
        AutofillEvent.host,
        AutofillEvent.schema_hash,
        AutofillEvent.gen_style_id,
        AutofillEvent.feedback_status,
        AutofillEvent.edit_chars,
    ).filter(AutofillEvent.gen_style_id.isnot(None))

    # Filter by date if needed
    if lookback_days > 0:
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        query = query.filter(AutofillEvent.created_at >= cutoff)

    # Aggregate results
    by_profile: Dict[Tuple[str, str], Dict[str, StyleStats]] = defaultdict(dict)

    for host, schema_hash, style_id, feedback_status, edit_chars in query:
        key = (host, schema_hash)

        if style_id not in by_profile[key]:
            by_profile[key][style_id] = StyleStats(style_id=style_id)

        st = by_profile[key][style_id]
        st.total_runs += 1

        # Count feedback
        if feedback_status == "helpful":
            st.helpful += 1
        elif feedback_status == "unhelpful":
            st.unhelpful += 1

        # Running average of edit_chars
        if edit_chars is not None:
            n = st.total_runs
            st.avg_edit_chars = ((st.avg_edit_chars * (n - 1)) + edit_chars) / n

    return by_profile


def _compute_family_style_stats(
    db: Session, lookback_days: int
) -> Dict[Tuple[str, str], StyleStats]:
    """
    Aggregate AutofillEvent by (host_family, gen_style_id).

    This enables cross-form generalization: if we don't have enough data
    for a specific form, we can use family-level statistics.

    Args:
        db: Database session
        lookback_days: Number of days to look back (0 = all time)

    Returns:
        Mapping of (family, style_id) to aggregated StyleStats

    Example:
        {
            ("greenhouse", "friendly_bullets_v1"): StyleStats(...),
            ("lever", "professional_narrative_v1"): StyleStats(...),
        }
    """
    query = db.query(
        AutofillEvent.host,
        AutofillEvent.gen_style_id,
        AutofillEvent.feedback_status,
        AutofillEvent.edit_chars,
    ).filter(AutofillEvent.gen_style_id.isnot(None))

    # Filter by date if needed
    if lookback_days > 0:
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        query = query.filter(AutofillEvent.created_at >= cutoff)

    # Aggregate by family
    family_stats: Dict[Tuple[str, str], StyleStats] = {}

    for host, style_id, feedback_status, edit_chars in query:
        if not host or not style_id:
            continue

        family = get_host_family(host)
        if not family:
            continue  # Host doesn't belong to any recognized family

        key = (family, style_id)

        if key not in family_stats:
            family_stats[key] = StyleStats(style_id=style_id)

        st = family_stats[key]
        st.total_runs += 1

        # Count feedback
        if feedback_status == "helpful":
            st.helpful += 1
        elif feedback_status == "unhelpful":
            st.unhelpful += 1

        # Running average of edit_chars
        if edit_chars is not None:
            n = st.total_runs
            st.avg_edit_chars = ((st.avg_edit_chars * (n - 1)) + edit_chars) / n

    return family_stats


def _compute_segment_style_stats(
    db: Session, lookback_days: int
) -> Dict[Tuple[str, str, str], StyleStats]:
    """
    Aggregate AutofillEvent by (host_family, segment_key, gen_style_id).

    This enables segment-aware tuning: different styles may work better
    for different role levels (e.g., interns vs seniors).

    Args:
        db: Database session
        lookback_days: Number of days to look back (0 = all time)

    Returns:
        Mapping of (family, segment_key, style_id) to aggregated StyleStats

    Example:
        {
            ("greenhouse", "senior", "professional_narrative_v1"): StyleStats(...),
            ("greenhouse", "intern", "friendly_bullets_v1"): StyleStats(...),
            ("lever", "senior", "concise_bullets_v1"): StyleStats(...),
        }
    """
    query = db.query(
        AutofillEvent.host,
        AutofillEvent.segment_key,
        AutofillEvent.gen_style_id,
        AutofillEvent.feedback_status,
        AutofillEvent.edit_chars,
    ).filter(
        AutofillEvent.gen_style_id.isnot(None),
        AutofillEvent.segment_key.isnot(None),  # Skip events without segment
    )

    # Filter by date if needed
    if lookback_days > 0:
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        query = query.filter(AutofillEvent.created_at >= cutoff)

    # Aggregate by (family, segment, style)
    segment_stats: Dict[Tuple[str, str, str], StyleStats] = {}

    for host, segment_key, style_id, feedback_status, edit_chars in query:
        if not host or not segment_key or not style_id:
            continue

        family = get_host_family(host)
        if not family:
            continue  # Host doesn't belong to any recognized family

        key = (family, segment_key, style_id)

        if key not in segment_stats:
            segment_stats[key] = StyleStats(style_id=style_id)

        st = segment_stats[key]
        st.total_runs += 1

        # Count feedback
        if feedback_status == "helpful":
            st.helpful += 1
        elif feedback_status == "unhelpful":
            st.unhelpful += 1

        # Running average of edit_chars
        if edit_chars is not None:
            n = st.total_runs
            st.avg_edit_chars = ((st.avg_edit_chars * (n - 1)) + edit_chars) / n

    return segment_stats


def _pick_best_style(styles: Dict[str, StyleStats]) -> Optional[StyleStats]:
    """
    Select best style by performance metrics.

    Ranking criteria (in order):
    1. Highest helpful_ratio (% of helpful feedback)
    2. Tie-breaker: Lowest avg_edit_chars
    3. Tie-breaker: Most total_runs (confidence)

    Args:
        styles: Dict of style_id -> StyleStats

    Returns:
        Best performing StyleStats or None if no styles
    """
    if not styles:
        return None

    return max(
        styles.values(),
        key=lambda s: (
            s.helpful_ratio,  # Primary: success rate
            -s.avg_edit_chars,  # Secondary: less editing needed
            s.total_runs,  # Tertiary: more data = more confidence
        ),
    )


def _pick_style_for_profile(
    host: str,
    schema_hash: str,
    form_stats: Dict[Tuple[str, str], Dict[str, StyleStats]],
    family_stats: Dict[Tuple[str, str], StyleStats],
    segment_stats: Dict[Tuple[str, str, str], StyleStats],
    segment_key: Optional[str] = None,
) -> Tuple[Optional[StyleStats], Dict[str, any]]:
    """
    Select best style for a profile using hierarchical fallback.

    Strategy (Phase 5.2):
    1. If form has enough samples (>= MIN_FORM_RUNS), use form-level best
    2. Else if segment+family has enough samples (>= MIN_SEGMENT_RUNS), use segment-level best
    3. Else if host's family has enough samples (>= MIN_FAMILY_RUNS), use family-level best
    4. Else return None (no recommendation)

    Args:
        host: Form host domain
        schema_hash: Form schema identifier
        form_stats: Per-form style statistics from _compute_style_stats
        family_stats: Per-family style statistics from _compute_family_style_stats
        segment_stats: Per-segment style statistics from _compute_segment_style_stats
        segment_key: Segment identifier (e.g., "senior", "intern")

    Returns:
        Tuple of (best StyleStats or None, metadata dict with source info)

    Example:
        # Form has 2 runs (not enough)
        # Segment "senior" at family "greenhouse" has 15 runs (enough)
        # Returns (style_stats, {"source": "segment", "segment_key": "senior"})
    """
    host = host or ""
    family = get_host_family(host)

    # Metadata about the decision
    meta = {"source": None, "segment_key": segment_key}

    # Collect all styles used on this specific form
    key = (host, schema_hash)
    form_styles = form_stats.get(key, {})

    # Strategy 1: Prefer per-form stats if any style has enough runs
    enough_form_samples = {
        sid: stats
        for sid, stats in form_styles.items()
        if stats.total_runs >= MIN_FORM_RUNS
    }

    if enough_form_samples:
        logger.debug(
            f"Using form-level stats for {host}/{schema_hash}: "
            f"{len(enough_form_samples)} styles with >= {MIN_FORM_RUNS} runs"
        )
        meta["source"] = "form"
        return _pick_best_style(enough_form_samples), meta

    # Strategy 2: Fall back to segment-level stats (Phase 5.2)
    if family and segment_key:
        segment_candidates = {
            stats.style_id: stats
            for (fam, seg, _sid), stats in segment_stats.items()
            if fam == family
            and seg == segment_key
            and stats.total_runs >= MIN_SEGMENT_RUNS
        }

        if segment_candidates:
            logger.debug(
                f"Using segment-level stats for {host}/{schema_hash} "
                f"(family={family}, segment={segment_key}): {len(segment_candidates)} styles "
                f"with >= {MIN_SEGMENT_RUNS} runs"
            )
            meta["source"] = "segment"
            return _pick_best_style(segment_candidates), meta

    # Strategy 3: Fall back to family-level stats (Phase 5.1)
    if family:
        family_candidates = {
            stats.style_id: stats
            for (fam, _sid), stats in family_stats.items()
            if fam == family and stats.total_runs >= MIN_FAMILY_RUNS
        }

        if family_candidates:
            logger.debug(
                f"Using family-level stats for {host}/{schema_hash} "
                f"(family={family}): {len(family_candidates)} styles "
                f"with >= {MIN_FAMILY_RUNS} runs"
            )
            meta["source"] = "family"
            return _pick_best_style(family_candidates), meta

    # Strategy 4: No recommendation
    logger.debug(
        f"No recommendation for {host}/{schema_hash}: "
        f"form_runs={sum(s.total_runs for s in form_styles.values())}, "
        f"segment={segment_key or 'none'}, "
        f"family={family or 'none'}"
    )
    return None, meta


def _update_style_hints(db: Session, lookback_days: int = 30) -> int:
    """
    Update FormProfile.style_hint with preferred_style_id based on feedback.

    Phase 5.0: Uses user feedback to recommend best performing style per form
    Phase 5.1: Falls back to family-level stats when form data is sparse
    Phase 5.2: Adds segment-aware tuning between form and family levels

    Args:
        db: Database session
        lookback_days: Number of days to analyze

    Returns:
        Number of profiles updated with style hints
    """
    # Compute style performance at all levels
    form_stats = _compute_style_stats(db, lookback_days)
    family_stats = _compute_family_style_stats(db, lookback_days)
    segment_stats = _compute_segment_style_stats(db, lookback_days)  # Phase 5.2

    if not form_stats and not family_stats and not segment_stats:
        logger.info("No style data found, skipping style hint updates")
        return 0

    # Get all profiles
    profiles = db.query(FormProfile).filter(FormProfile.host.isnot(None)).all()

    updated = 0
    for profile in profiles:
        # Phase 5.2: Derive segment_key for this profile
        # We need to get a representative event to extract segment
        # For now, use the most common segment_key for this profile
        segment_key = (
            db.query(AutofillEvent.segment_key)
            .filter(
                AutofillEvent.host == profile.host,
                AutofillEvent.schema_hash == profile.schema_hash,
                AutofillEvent.segment_key.isnot(None),
            )
            .order_by(func.count(AutofillEvent.id).desc())
            .group_by(AutofillEvent.segment_key)
            .first()
        )
        segment_key = segment_key[0] if segment_key else None

        # Use hierarchical selection (form → segment → family)
        best, meta = _pick_style_for_profile(
            host=profile.host,
            schema_hash=profile.schema_hash,
            form_stats=form_stats,
            family_stats=family_stats,
            segment_stats=segment_stats,
            segment_key=segment_key,
        )

        if not best:
            continue  # No recommendation for this profile

        # Build/update style_hint
        hint = (profile.style_hint or {}).copy()
        old_style = hint.get("preferred_style_id")

        if old_style == best.style_id:
            continue  # No change needed

        hint["preferred_style_id"] = best.style_id

        # Phase 5.2: Record source and segment_key in hint
        hint["source"] = meta["source"]
        if meta["source"] == "segment" and segment_key:
            hint["segment_key"] = segment_key

        # Include detailed stats (form-level if available, else family-level)
        key = (profile.host, profile.schema_hash)
        styles_for_profile = form_stats.get(key, {})

        if styles_for_profile:
            # Use form-level stats for display
            hint["style_stats"] = {
                sid: {
                    "helpful": s.helpful,
                    "unhelpful": s.unhelpful,
                    "total_runs": s.total_runs,
                    "helpful_ratio": s.helpful_ratio,
                    "avg_edit_chars": s.avg_edit_chars,
                }
                for sid, s in styles_for_profile.items()
            }
        else:
            # Use family-level stats for display
            family = get_host_family(profile.host)
            if family:
                hint["bundle_stats"] = {
                    best.style_id: {
                        "helpful": best.helpful,
                        "unhelpful": best.unhelpful,
                        "total_runs": best.total_runs,
                        "helpful_ratio": best.helpful_ratio,
                        "avg_edit_chars": best.avg_edit_chars,
                        "source": f"family:{family}",
                    }
                }

        profile.style_hint = hint
        updated += 1

        logger.info(
            f"Updated style hint for {profile.host}/{profile.schema_hash}: "
            f"preferred={best.style_id} "
            f"(source={meta['source']}, "
            f"helpful_ratio={best.helpful_ratio:.1%}, "
            f"avg_edit_chars={best.avg_edit_chars:.1f})"
        )

    return updated


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
    counts: Dict[str, CollectionsCounter] = defaultdict(CollectionsCounter)

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
    6. Phase 5.0: Update style_hint with preferred_style_id

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

    # Phase 5.0: Update style hints for all profiles
    style_updates = _update_style_hints(db, lookback_days=days)
    logger.info(f"Updated style hints for {style_updates} profiles")

    return updated


def run_aggregator(days: int = 30) -> int:
    """
    Entry point for CLI / cron container.

    Opens a database session, runs aggregation, commits changes.

    Emits Prometheus metrics:
    - applylens_autofill_agg_runs_total{status="ok|err"}
    - applylens_autofill_profiles_updated_total

    Usage:
        python -c "from app.autofill_aggregator import run_aggregator; print(run_aggregator(days=30))"
    """
    db = SessionLocal()
    try:
        updated = aggregate_autofill_profiles(db, days=days)
        db.commit()

        # Track metrics
        autofill_agg_runs_total.labels(status="ok").inc()
        autofill_profiles_updated_total.inc(updated)

        logger.info(f"Aggregation complete: {updated} profiles updated")
        return updated
    except Exception as e:
        db.rollback()
        autofill_agg_runs_total.labels(status="err").inc()
        logger.error(f"Aggregation failed: {e}")
        raise
    finally:
        db.close()
