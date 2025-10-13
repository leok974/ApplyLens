"""
Default Policy Seeds for Phase 4 Agentic Actions

Provides sensible default policies for common email automation scenarios:
- Auto-archive expired promotions
- Quarantine high-risk emails
- Auto-label job applications
- Create calendar events from invitations
"""

from sqlalchemy.orm import Session

from ..models import ActionType, Policy

DEFAULT_POLICIES = [
    {
        "name": "Promo auto-archive",
        "enabled": True,
        "priority": 50,
        "action": ActionType.archive_email,
        "confidence_threshold": 0.7,
        "condition": {
            "all": [
                {"eq": ["category", "promotions"]},
                {"exists": ["expires_at"]},
                {"lt": ["expires_at", "now"]},
            ]
        },
    },
    {
        "name": "High-risk quarantine",
        "enabled": True,
        "priority": 10,  # Higher priority (runs first)
        "action": ActionType.quarantine_attachment,
        "confidence_threshold": 0.0,  # Always execute if condition matches
        "condition": {"gte": ["risk_score", 80]},
    },
    {
        "name": "Job application auto-label",
        "enabled": True,
        "priority": 30,
        "action": ActionType.label_email,
        "confidence_threshold": 0.75,
        "condition": {
            "all": [
                {"eq": ["category", "applications"]},
                {"regex": ["subject", "(?i)(application|interview|offer)"]},
            ]
        },
    },
    {
        "name": "Create event from invitation",
        "enabled": False,  # Disabled by default (requires calendar integration)
        "priority": 40,
        "action": ActionType.create_calendar_event,
        "confidence_threshold": 0.8,
        "condition": {
            "all": [
                {"eq": ["category", "events"]},
                {"exists": ["event_start_at"]},
                {"regex": ["subject", "(?i)(invitation|invite|meeting|event)"]},
            ]
        },
    },
    {
        "name": "Auto-unsubscribe inactive senders",
        "enabled": False,  # Disabled by default (user opt-in)
        "priority": 60,
        "action": ActionType.unsubscribe_via_header,
        "confidence_threshold": 0.9,
        "condition": {
            "all": [
                {"eq": ["category", "promotions"]},
                {"gte": ["age_days", 90]},
                {"exists": ["sender_domain"]},
            ]
        },
    },
]


def seed_policies(db: Session) -> int:
    """
    Seed default policies into database.

    Args:
        db: SQLAlchemy session

    Returns:
        Number of policies created (skips existing)
    """
    created = 0

    for policy_data in DEFAULT_POLICIES:
        # Check if policy already exists
        existing = db.query(Policy).filter(Policy.name == policy_data["name"]).first()
        if existing:
            print(f"[SEED] Policy '{policy_data['name']}' already exists, skipping")
            continue

        # Create new policy
        policy = Policy(**policy_data)
        db.add(policy)
        created += 1
        print(f"[SEED] Created policy: {policy_data['name']}")

    db.commit()
    print(f"[SEED] Seeded {created} policies")
    return created


def reset_policies(db: Session) -> None:
    """
    Delete all policies and reseed defaults.

    WARNING: This will delete all existing policies!
    """
    # Delete all policies
    db.query(Policy).delete()
    db.commit()
    print("[SEED] Deleted all existing policies")

    # Reseed defaults
    seed_policies(db)


if __name__ == "__main__":
    # Allow running as script
    from ..db import SessionLocal

    db = SessionLocal()
    try:
        seed_policies(db)
    finally:
        db.close()
