"""
Auto-match service for nightly job opportunity matching.

Runs batch role matching for all users with active resume profiles.
"""

import logging
from sqlalchemy.orm import Session

from app.models import ResumeProfile
from app.agent.orchestrator import MailboxAgentOrchestrator
from app.config import RequestContext
from app.schemas_agent import RoleMatchBatchRequest

logger = logging.getLogger(__name__)


async def auto_match_all_opportunities(db: Session) -> int:
    """
    For all users with an active resume profile, match all unmatched opportunities.

    Args:
        db: Synchronous database session

    Returns:
        Total number of opportunities processed across all users.
    """
    total_processed = 0

    # Find all users with active resumes (synchronous query)
    users_with_resumes = (
        db.query(ResumeProfile.owner_email)
        .filter(ResumeProfile.is_active == True)  # noqa: E712
        .distinct()
        .all()
    )

    logger.info(
        f"Auto-match: found {len(users_with_resumes)} users with active resumes"
    )

    for (owner_email,) in users_with_resumes:
        try:
            # Create context for this user
            ctx = RequestContext(user_id=owner_email, db_session=db)
            orchestrator = MailboxAgentOrchestrator(ctx=ctx)

            # Run batch match with no limit (process all unmatched)
            batch_req = RoleMatchBatchRequest(limit=None)
            resp = await orchestrator.role_match_batch(batch_req)

            total_processed += resp.processed
            logger.info(
                f"Auto-match: processed {resp.processed} opportunities for {owner_email}"
            )

        except Exception as e:
            logger.error(
                f"Auto-match failed for user {owner_email}: {e}",
                exc_info=True,
            )
            # Continue with other users
            continue

    logger.info(f"Auto-match: total processed {total_processed} opportunities")
    return total_processed
