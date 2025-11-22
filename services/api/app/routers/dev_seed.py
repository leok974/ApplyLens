"""
Dev-only endpoint for seeding test data.
Only available when ALLOW_DEV_ROUTES=1 environment variable is set.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import logging
import os

from app.auth.deps import current_user
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/dev",
    tags=["dev"],
)


class SeedThread(BaseModel):
    thread_id: str
    subject: str
    from_addr: str
    risk_level: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    summary_headline: str
    summary_details: List[str]


class SeedResult(BaseModel):
    ok: bool
    count: int


class SeedCountRequest(BaseModel):
    count: int = 40


@router.post("/seed-threads-simple", response_model=SeedResult)
async def seed_threads_simple(
    request: SeedCountRequest,
    user: Optional[User] = Depends(current_user),
):
    """
    Simplified seed endpoint that generates N threads with realistic job-search content.

    Security:
    - Only available when ALLOW_DEV_ROUTES=1 environment variable is set.
    - Requires authenticated user.
    """

    if not user:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_email = user.email

    # SECURITY GUARD:
    if os.getenv("ALLOW_DEV_ROUTES") != "1":
        raise HTTPException(status_code=403, detail="dev routes disabled")

    logger.info("[DEV SEED] seeding %d threads for %s", request.count, user_email)

    # Import ES client
    from app.es import es, ES_ENABLED, INDEX
    from datetime import datetime, timezone, timedelta
    import random

    if not ES_ENABLED or es is None:
        logger.warning("[DEV SEED] Elasticsearch not enabled, skipping seed")
        return SeedResult(ok=True, count=0)

    # Sample data for generating realistic threads
    companies = [
        "TechCorp",
        "StartupInc",
        "BigTech Co",
        "InnovateNow",
        "DataSystems",
        "CloudWorks",
    ]
    roles = [
        "Senior Engineer",
        "ML Engineer",
        "Backend Developer",
        "Full Stack Developer",
        "Data Scientist",
    ]
    senders = ["recruiter@{}.com", "jobs@{}.com", "talent@{}.com", "hiring@{}.com"]

    seeded_count = 0
    for i in range(request.count):
        try:
            company = random.choice(companies)
            role = random.choice(roles)
            sender_template = random.choice(senders)
            sender = sender_template.format(company.lower().replace(" ", ""))

            thread_id = f"seed-thread-{i}-{random.randint(1000, 9999)}"
            risk_score = random.choice([10, 10, 10, 40, 70])  # Mostly low risk

            # Build ES document
            doc = {
                "gmail_id": thread_id,
                "thread_id": thread_id,
                "subject": f"{role} position at {company}",
                "sender": sender,
                "from_addr": sender,
                "recipient": user_email,
                "owner_email": user_email,
                "received_at": (
                    datetime.now(timezone.utc) - timedelta(hours=i)
                ).isoformat(),
                "labels": ["UNREAD", "INBOX"],
                "label_heuristics": [],
                "risk_score": risk_score,
                "quarantined": False,
                "user_archived": False,
                "user_overrode_safe": False,
                "user_unsubscribed": False,
                "archived": False,
                "muted": False,
                "unread": True,
                "category": random.choice(["interview", "offer", "application"]),
                "summary_headline": f"Interview opportunity for {role}",
                "summary_details": [
                    f"Position: {role} at {company}",
                    "Remote-friendly team",
                    "Competitive compensation",
                ],
                "timeline": [
                    {
                        "actor": sender,
                        "ts": (
                            datetime.now(timezone.utc) - timedelta(hours=i)
                        ).isoformat(),
                        "note": "Initial message received",
                        "kind": "received",
                    }
                ],
                "body_text": f"Hi,\n\nWe're hiring for a {role} position at {company}. Would love to chat!",
            }

            # Index to ES
            es.index(index=INDEX, id=thread_id, body=doc)
            seeded_count += 1

        except Exception as e:
            logger.error("[DEV SEED] Failed to seed thread %d: %s", i, e)
            continue

    logger.info(
        "[DEV SEED] Successfully seeded %d/%d threads", seeded_count, request.count
    )
    return SeedResult(ok=True, count=seeded_count)


@router.post("/seed-threads", response_model=SeedResult)
async def seed_threads(
    threads: List[SeedThread],
    user: Optional[User] = Depends(current_user),
):
    """
    Insert mock thread rows for E2E tests so /inbox isn't empty.

    Requirements:
    - DOES NOT send real Gmail calls.
    - Writes to the same backing store the Inbox page queries (Postgres+ES doc, whatever you're listing in Inbox).
    - Safe to call repeatedly; either upsert, or just overwrite in-memory cache if you're faking it.

    Security:
    - Only available when ALLOW_DEV_ROUTES=1 environment variable is set.
    - Requires authenticated user.
    """

    if not user:
        raise HTTPException(status_code=401, detail="unauthorized")

    user_email = user.email

    # SECURITY GUARD:
    # Only allow this route when ALLOW_DEV_ROUTES=1
    if os.getenv("ALLOW_DEV_ROUTES") != "1":
        raise HTTPException(status_code=403, detail="dev routes disabled")

    logger.info("[DEV SEED] inbox seeding %d threads for %s", len(threads), user_email)

    # Import ES client
    from app.es import es, ES_ENABLED, INDEX
    from datetime import datetime, timezone

    if not ES_ENABLED or es is None:
        logger.warning("[DEV SEED] Elasticsearch not enabled, skipping seed")
        return SeedResult(ok=True, count=0)

    # Map risk level string to numeric score
    risk_level_map = {
        "LOW": 10,
        "MEDIUM": 40,
        "HIGH": 70,
        "CRITICAL": 95,
    }

    seeded_count = 0
    for thread in threads:
        try:
            # Convert risk level to score
            risk_score = risk_level_map.get(thread.risk_level.upper(), 10)

            # Build ES document matching the structure expected by /api/inbox
            doc = {
                "gmail_id": thread.thread_id,
                "thread_id": thread.thread_id,
                "subject": thread.subject,
                "sender": thread.from_addr,
                "from_addr": thread.from_addr,
                "recipient": user_email,
                "owner_email": user_email,
                "received_at": datetime.now(timezone.utc).isoformat(),
                "labels": ["UNREAD", "INBOX"],
                "label_heuristics": [],
                "risk_score": risk_score,
                "quarantined": False,
                "user_archived": False,
                "user_overrode_safe": False,
                "user_unsubscribed": False,
                "archived": False,
                "muted": False,
                "unread": True,
                "category": "interview"
                if "interview" in thread.subject.lower()
                else "offer",
                # Add summary fields for ThreadViewer
                "summary_headline": thread.summary_headline,
                "summary_details": thread.summary_details,
                # Add timeline for conversation view
                "timeline": [
                    {
                        "actor": thread.from_addr,
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "note": "Initial message received",
                        "kind": "received",
                    }
                ],
                "body_text": f"{thread.summary_headline}\n\n"
                + "\n".join(thread.summary_details),
            }

            # Index to ES (upsert using thread_id as document ID)
            es.index(index=INDEX, id=thread.thread_id, body=doc)
            seeded_count += 1
            logger.info("[DEV SEED] Indexed thread %s", thread.thread_id)

        except Exception as e:
            logger.error("[DEV SEED] Failed to seed thread %s: %s", thread.thread_id, e)
            continue

    logger.info(
        "[DEV SEED] Successfully seeded %d/%d threads", seeded_count, len(threads)
    )
    return SeedResult(ok=True, count=seeded_count)
