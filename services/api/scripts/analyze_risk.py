#!/usr/bin/env python3
"""
Risk Scoring Script - Nightly Automation Job

Recomputes risk_score for all emails using heuristic-based scoring.
Stores score breakdown in features_json for analytics.

Risk Score Components (0-100 scale):
- Sender domain trust: 40 points
- Subject keywords: 40 points
- Source confidence: 20 points

Usage:
    # Process all emails
    python scripts/analyze_risk.py

    # Process specific batch size
    BATCH_SIZE=1000 python scripts/analyze_risk.py

    # Dry run (no database updates)
    DRY_RUN=1 python scripts/analyze_risk.py

Environment Variables:
    BATCH_SIZE  - Number of emails to process per batch (default: 500)
    DRY_RUN     - If set to 1, only print changes without updating DB
    DATABASE_URL - PostgreSQL connection string
"""

import os
import sys
import datetime as dt
from typing import Dict, Tuple, Any
from sqlalchemy import select, func

# Add app to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import get_db
from app.models import Email
from app.utils.schema_guard import require_min_migration

# Configuration
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"

# Heuristic weights (must sum to 1.0 for normalized 0-100 scale)
WEIGHTS = {"sender_domain": 0.4, "subject_keywords": 0.4, "source_confidence": 0.2}

# Suspicious keywords in subject lines
SUSPICIOUS_KEYWORDS = [
    "urgent",
    "action required",
    "verify",
    "suspended",
    "locked",
    "confirm",
    "click here",
    "act now",
    "limited time",
    "expire",
    "password",
    "security alert",
    "unusual activity",
    "billing issue",
    "account update",
    "re-activate",
    "immediate action",
]

# Trusted domains (low risk)
TRUSTED_DOMAINS = [
    "gmail.com",
    "outlook.com",
    "hotmail.com",
    "yahoo.com",
    "protonmail.com",
    "icloud.com",
    "fastmail.com",
]

# Known recruiter/ATS domains (medium-low risk)
RECRUITER_DOMAINS = [
    "greenhouse.io",
    "lever.co",
    "workday.com",
    "bamboohr.com",
    "jobvite.com",
    "smartrecruiters.com",
    "icims.com",
]


def extract_domain(email_address: str) -> str:
    """Extract domain from email address."""
    if not email_address:
        return ""

    # Handle format: "Name <email@domain.com>"
    if "<" in email_address and ">" in email_address:
        email_address = email_address.split("<")[1].split(">")[0]

    # Extract domain
    parts = email_address.split("@")
    return parts[1] if len(parts) > 1 else ""


def compute_sender_domain_risk(sender: str) -> Tuple[float, Dict[str, Any]]:
    """
    Compute risk score based on sender domain.

    Returns:
        - score: 0-40 points (40 = high risk, 0 = trusted)
        - details: breakdown with domain and trust level
    """
    domain = extract_domain(sender).lower()

    # Trusted domains: 0 points (safe)
    if domain in TRUSTED_DOMAINS:
        return 0.0, {"domain": domain, "trust_level": "trusted", "points": 0.0}

    # Known recruiter/ATS domains: 10 points (low risk)
    if domain in RECRUITER_DOMAINS or any(
        x in domain for x in ["greenhouse", "lever", "workday"]
    ):
        return 10.0, {"domain": domain, "trust_level": "recruiter", "points": 10.0}

    # Unknown domains: 40 points (high risk)
    return 40.0, {"domain": domain, "trust_level": "unknown", "points": 40.0}


def compute_subject_keyword_risk(subject: str) -> Tuple[float, Dict[str, Any]]:
    """
    Compute risk score based on suspicious keywords in subject.

    Returns:
        - score: 0-40 points (more keywords = higher risk)
        - details: matched keywords and points
    """
    if not subject:
        return 0.0, {"keywords": [], "points": 0.0}

    subject_lower = subject.lower()
    matched = [kw for kw in SUSPICIOUS_KEYWORDS if kw in subject_lower]

    if not matched:
        return 0.0, {"keywords": [], "points": 0.0}

    # Scale: 1 keyword = 20 points, 2+ = 40 points
    score = min(40.0, len(matched) * 20.0)

    return score, {"keywords": matched, "count": len(matched), "points": score}


def compute_source_confidence_risk(
    source_confidence: float,
) -> Tuple[float, Dict[str, Any]]:
    """
    Compute risk score based on source confidence.

    Lower confidence = higher risk.

    Returns:
        - score: 0-20 points (inverse of confidence * 20)
        - details: confidence value and points
    """
    if source_confidence is None:
        # No confidence data: assume medium risk
        return 10.0, {"confidence": None, "points": 10.0}

    # Invert: high confidence (1.0) = low risk (0 points)
    #         low confidence (0.0) = high risk (20 points)
    score = (1.0 - source_confidence) * 20.0

    return score, {"confidence": source_confidence, "points": round(score, 2)}


def compute_risk_score(email: Email) -> Tuple[float, Dict[str, Any]]:
    """
    Compute total risk score and breakdown for an email.

    Returns:
        - total_score: 0-100 (sum of all components)
        - breakdown: detailed scoring components
    """
    sender_score, sender_details = compute_sender_domain_risk(email.sender or "")
    subject_score, subject_details = compute_subject_keyword_risk(email.subject or "")
    confidence_score, confidence_details = compute_source_confidence_risk(
        email.source_confidence
    )

    total = sender_score + subject_score + confidence_score

    breakdown = {
        "total_score": round(total, 2),
        "computed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "components": {
            "sender_domain": sender_details,
            "subject_keywords": subject_details,
            "source_confidence": confidence_details,
        },
        "weights": WEIGHTS,
    }

    return round(total, 2), breakdown


def analyze_batch(db, limit: int = BATCH_SIZE, offset: int = 0) -> Tuple[int, int]:
    """
    Analyze a batch of emails and update their risk scores.

    Returns:
        - processed: number of emails processed
        - updated: number of emails with changed scores
    """
    # Fetch batch
    stmt = select(Email).limit(limit).offset(offset)
    result = db.execute(stmt)
    emails = result.scalars().all()

    if not emails:
        return 0, 0

    processed = 0
    updated = 0

    for email in emails:
        processed += 1

        # Compute new risk score
        new_score, breakdown = compute_risk_score(email)

        # Check if score changed (avoid unnecessary updates)
        score_changed = email.risk_score != new_score

        if score_changed or not email.features_json:
            if not DRY_RUN:
                email.risk_score = new_score
                email.features_json = breakdown
            updated += 1

            if DRY_RUN and updated <= 5:
                print(f"  [DRY RUN] Email {email.id}: {email.risk_score} → {new_score}")
                print(f"    Sender: {email.sender}")
                print(f"    Subject: {email.subject[:50]}...")
                print(f"    Breakdown: {breakdown['components']}")

    if not DRY_RUN:
        db.commit()

    return processed, updated


def run():
    """Main execution function."""
    # Schema guard: Ensure database has required columns
    print("Checking database schema...")
    try:
        require_min_migration(
            "0012_add_emails_features_json", "email automation system fields"
        )
        print("✓ Database schema validation passed\n")
    except RuntimeError as e:
        print(f"❌ Schema validation failed:\n{e}", file=sys.stderr)
        sys.exit(1)

    db = next(get_db())

    # Get total count
    total_count = db.execute(select(func.count(Email.id))).scalar()

    print("Risk Scoring Analysis")
    print(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE UPDATE'}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Total emails: {total_count}")
    print("-" * 60)

    start_time = dt.datetime.now()
    total_processed = 0
    total_updated = 0
    offset = 0

    while True:
        processed, updated = analyze_batch(db, BATCH_SIZE, offset)

        if processed == 0:
            break

        total_processed += processed
        total_updated += updated
        offset += BATCH_SIZE

        print(
            f"Progress: {total_processed}/{total_count} emails processed, {total_updated} updated"
        )

    duration = (dt.datetime.now() - start_time).total_seconds()

    print("-" * 60)
    print(f"Risk scoring {'(DRY RUN) ' if DRY_RUN else ''}completed")
    print(f"Total processed: {total_processed}")
    print(f"Total updated: {total_updated}")
    print(f"Unchanged: {total_processed - total_updated}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Rate: {total_processed / duration:.1f} emails/sec")


if __name__ == "__main__":
    run()
