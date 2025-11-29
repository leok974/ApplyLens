"""Unit tests for opportunity priority scoring logic."""

from datetime import datetime, timedelta, timezone

from app.routers.opportunities import (
    _age_bonus,
    compute_opportunity_priority,
)


def _days_ago(days: int) -> datetime:
    """Helper to create a datetime N days in the past."""
    return datetime.now(timezone.utc) - timedelta(days=days)


# ===== Age Bonus Tests =====


def test_age_bonus_very_recent():
    """Messages ≤ 3 days old should get +2 bonus."""
    assert _age_bonus(_days_ago(1)) == 2
    assert _age_bonus(_days_ago(2)) == 2
    # Day 3 is exactly at boundary - implementation uses <= 3, so it gets +2
    # But in practice, 3 days ago is slightly over 3.0 days, so it gets +1
    assert _age_bonus(_days_ago(2.5)) == 2


def test_age_bonus_recent():
    """Messages 3 < days ≤ 7 should get +1 bonus."""
    assert _age_bonus(_days_ago(3)) == 1  # Just over 3 days
    assert _age_bonus(_days_ago(4)) == 1
    assert _age_bonus(_days_ago(5)) == 1
    assert _age_bonus(_days_ago(6)) == 1
    # Day 7 is exactly at boundary - same issue as day 3
    assert _age_bonus(_days_ago(6.5)) == 1


def test_age_bonus_moderate():
    """Messages 7 < days ≤ 21 should get 0 bonus."""
    assert _age_bonus(_days_ago(7)) == 0  # Just over 7 days
    assert _age_bonus(_days_ago(8)) == 0
    assert _age_bonus(_days_ago(14)) == 0
    assert _age_bonus(_days_ago(20)) == 0
    # Day 21 boundary
    assert _age_bonus(_days_ago(20.5)) == 0


def test_age_bonus_old():
    """Messages > 21 days old should get -1 penalty."""
    assert _age_bonus(_days_ago(22)) == -1
    assert _age_bonus(_days_ago(30)) == -1
    assert _age_bonus(_days_ago(60)) == -1


def test_age_bonus_none():
    """None timestamp should return 0."""
    assert _age_bonus(None) == 0


def test_age_bonus_naive_datetime():
    """Naive datetime (no timezone) should be treated as UTC."""
    naive_dt = datetime.now() - timedelta(days=2)
    assert _age_bonus(naive_dt) == 2


# ===== Priority Computation Tests =====


def test_offer_recent_is_high():
    """Offer that's recent should be high priority.

    Score: 4 (offer) + 2 (age ≤3) + 1 (good category) = 7 → high
    """
    priority = compute_opportunity_priority(
        application_status="offer",
        email_category="offer",
        last_message_at=_days_ago(1),
    )
    assert priority == "high"


def test_interview_invite_mid_age_is_high():
    """Interview invite 5 days ago should be high priority.

    Score: 2 (interview from status) + 1 (age 4-7) + 1 (good category) = 4 → high
    """
    priority = compute_opportunity_priority(
        application_status="interview",
        email_category="interview_invite",
        last_message_at=_days_ago(5),
    )
    assert priority == "high"


def test_onsite_recent_is_high():
    """Onsite interview recent should be high priority.

    Score: 3 (onsite) + 2 (age ≤3) + 1 (good category) = 6 → high
    """
    priority = compute_opportunity_priority(
        application_status="onsite",
        email_category="onsite",
        last_message_at=_days_ago(2),
    )
    assert priority == "high"


def test_applied_recent_is_high():
    """Recently applied with recruiter outreach should be high priority.

    Score: 1 (applied) + 2 (age ≤3) + 1 (recruiter_outreach in good cats) = 4 → high
    """
    priority = compute_opportunity_priority(
        application_status="applied",
        email_category="recruiter_outreach",
        last_message_at=_days_ago(2),
    )
    assert priority == "high"


def test_applied_old_is_medium():
    """Applied 6 days ago should be medium priority.

    Score: 1 (applied) + 1 (age 4-7) + 1 (recruiter_outreach) = 3 → medium (score >=  2, < 4)
    """
    priority = compute_opportunity_priority(
        application_status="applied",
        email_category="recruiter_outreach",
        last_message_at=_days_ago(6),
    )
    assert priority == "medium"


def test_phone_screen_moderate_age_is_medium():
    """Phone screen 10 days ago should be medium priority.

    Score: 2 (phone_screen) + 0 (age 8-21) + 1 (good category) = 3 → medium
    """
    priority = compute_opportunity_priority(
        application_status="phone_screen",
        email_category="phone_screen",
        last_message_at=_days_ago(10),
    )
    assert priority == "medium"


def test_old_outreach_is_low():
    """Old recruiter outreach should be low priority.

    Score: 1 (recruiter_outreach from status) + (-1) (age >21) + 0 (not in good cats) = 0 → low
    """
    priority = compute_opportunity_priority(
        application_status="applied",
        email_category="recruiter_outreach",
        last_message_at=_days_ago(30),
    )
    assert priority == "low"


def test_unknown_status_old_is_low():
    """Unknown status and old should be low priority.

    Score: 0 (unknown) + (-1) (age >21) + 0 = -1 → low
    """
    priority = compute_opportunity_priority(
        application_status="unknown_status",
        email_category="general",
        last_message_at=_days_ago(25),
    )
    assert priority == "low"


def test_negotiation_very_recent_is_high():
    """Negotiation stage very recent should be high priority.

    Score: 4 (negotiation) + 2 (age ≤3) + 0 (category not in good) = 6 → high
    """
    priority = compute_opportunity_priority(
        application_status="negotiation",
        email_category="negotiation",
        last_message_at=_days_ago(1),
    )
    assert priority == "high"


def test_fallback_to_category_hints():
    """When status is None, should use category hints.

    Score: 3 (interview_invite from category) + 2 (age ≤3) + 1 (good cat) = 6 → high
    """
    priority = compute_opportunity_priority(
        application_status=None,
        email_category="interview_invite",
        last_message_at=_days_ago(2),
    )
    assert priority == "high"


def test_case_insensitive_status():
    """Status matching should be case-insensitive.

    Score: 4 (OFFER) + 2 (age ≤3) + 1 (good cat) = 7 → high
    """
    priority = compute_opportunity_priority(
        application_status="OFFER",
        email_category="OFFER",
        last_message_at=_days_ago(1),
    )
    assert priority == "high"


def test_hr_screen_recent_is_high():
    """HR screen recent should be high priority.

    Score: 2 (hr_screen) + 2 (age ≤3) + 1 (hr_screen in good cats) = 5 → high
    """
    priority = compute_opportunity_priority(
        application_status="hr_screen",
        email_category="hr_screen",
        last_message_at=_days_ago(2),
    )
    assert priority == "high"


def test_final_round_moderate_age_is_medium():
    """Final round 8 days ago should be medium priority.

    Score: 3 (final_round) + 0 (age 8-21) + 0 = 3 → medium
    """
    priority = compute_opportunity_priority(
        application_status="final_round",
        email_category="final_round",
        last_message_at=_days_ago(8),
    )
    assert priority == "medium"


def test_no_data_is_low():
    """No status, category, or timestamp should be low priority.

    Score: 0 + 0 + 0 = 0 → low
    """
    priority = compute_opportunity_priority(
        application_status=None,
        email_category=None,
        last_message_at=None,
    )
    assert priority == "low"
