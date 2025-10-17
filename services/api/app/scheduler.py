"""Scheduled jobs for ApplyLens.

Uses APScheduler for background tasks like feed loading, weight updates, etc.
"""

import logging
from contextlib import contextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.db import SessionLocal

logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler()


@contextmanager
def session_scope():
    """Provide a transactional scope for database operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Session error: {e}")
        raise
    finally:
        session.close()


def is_active_learning_paused(session: Session) -> bool:
    """Check if active learning is paused."""
    from app.models import RuntimeSetting
    
    setting = session.query(RuntimeSetting).filter_by(key="active_learning.paused").first()
    return setting and setting.value == "true"


# ============================================================================
# Active Learning Jobs (Phase 5.3)
# ============================================================================

def job_load_labeled_data():
    """Daily job: Load labeled data from all sources."""
    logger.info("Starting scheduled job: load_labeled_data")
    
    try:
        with session_scope() as session:
            # Check if paused
            if is_active_learning_paused(session):
                logger.info("Active learning is paused, skipping labeled data loading")
                return
            
            from app.active.feeds import load_all_feeds
            
            counts = load_all_feeds(session)
            total = sum(counts.values())
            
            logger.info(f"Loaded {total} labeled examples: {counts}")
    except Exception as e:
        logger.error(f"Failed to load labeled data: {e}", exc_info=True)


def job_update_judge_weights():
    """Daily job: Update judge reliability weights."""
    logger.info("Starting scheduled job: update_judge_weights")
    
    try:
        with session_scope() as session:
            # Check if paused
            if is_active_learning_paused(session):
                logger.info("Active learning is paused, skipping judge weight update")
                return
            
            from app.active.weights import nightly_update_weights
            
            results = nightly_update_weights(session)
            
            logger.info(f"Updated judge weights for {len(results)} agents")
            for agent, weights in results.items():
                logger.info(f"  {agent}: {weights}")
    except Exception as e:
        logger.error(f"Failed to update judge weights: {e}", exc_info=True)


def job_sample_review_queue():
    """Daily job: Sample uncertain predictions for review."""
    logger.info("Starting scheduled job: sample_review_queue")
    
    try:
        with session_scope() as session:
            # Check if paused
            if is_active_learning_paused(session):
                logger.info("Active learning is paused, skipping review queue sampling")
                return
            
            from app.active.sampler import daily_sample_review_queue
            
            candidates = daily_sample_review_queue(session, top_n_per_agent=20)
            total = sum(len(c) for c in candidates.values())
            
            logger.info(f"Sampled {total} review queue candidates across {len(candidates)} agents")
            for agent, agent_candidates in candidates.items():
                logger.info(f"  {agent}: {len(agent_candidates)} candidates")
    except Exception as e:
        logger.error(f"Failed to sample review queue: {e}", exc_info=True)


def job_watch_incidents():
    """Every 15 min: Watch for invariant failures and raise incidents."""
    logger.info("Starting scheduled job: watch_incidents")
    
    try:
        from app.intervene.watcher import run_watcher_cycle
        run_watcher_cycle()
    except Exception as e:
        logger.error(f"Failed to run watcher cycle: {e}", exc_info=True)


def job_check_canary_deployments():
    """Daily job: Check canary deployments and auto-promote/rollback."""
    logger.info("Starting scheduled job: check_canary_deployments")
    
    try:
        with session_scope() as session:
            # Check if paused
            if is_active_learning_paused(session):
                logger.info("Active learning is paused, skipping canary checks")
                return
            
            from app.active.guards import OnlineLearningGuard
            
            guard = OnlineLearningGuard(session)
            results = guard.nightly_guard_check()
            
            logger.info(f"Checked {len(results)} active canaries")
            for agent, result in results.items():
                logger.info(f"  {agent}: {result.get('status', 'unknown')}")
                
                if result.get("status") == "rolled_back":
                    logger.warning(f"Auto-rolled back canary for {agent}: {result.get('reason')}")
                elif result.get("status") == "promoted":
                    logger.info(f"Promoted {agent} from {result.get('from_percent')}% to {result.get('to_percent')}%")
    except Exception as e:
        logger.error(f"Failed to check canary deployments: {e}", exc_info=True)


# ============================================================================
# Schedule Configuration
# ============================================================================

def setup_scheduled_jobs():
    """Configure and start all scheduled jobs."""
    logger.info("Setting up scheduled jobs...")
    
    # Active Learning Jobs (Phase 5.3)
    
    # Daily at 2 AM: Load labeled data
    scheduler.add_job(
        job_load_labeled_data,
        trigger=CronTrigger(hour=2, minute=0),
        id="load_labeled_data",
        name="Load Labeled Data",
        replace_existing=True
    )
    logger.info("Scheduled: Load labeled data (daily at 2 AM)")
    
    # Daily at 3 AM: Update judge weights
    scheduler.add_job(
        job_update_judge_weights,
        trigger=CronTrigger(hour=3, minute=0),
        id="update_judge_weights",
        name="Update Judge Weights",
        replace_existing=True
    )
    logger.info("Scheduled: Update judge weights (daily at 3 AM)")
    
    # Daily at 4 AM: Sample review queue
    scheduler.add_job(
        job_sample_review_queue,
        trigger=CronTrigger(hour=4, minute=0),
        id="sample_review_queue",
        name="Sample Review Queue",
        replace_existing=True
    )
    logger.info("Scheduled: Sample review queue (daily at 4 AM)")
    
    # Daily at 5 AM: Check canary deployments
    scheduler.add_job(
        job_check_canary_deployments,
        trigger=CronTrigger(hour=5, minute=0),
        id="check_canary_deployments",
        name="Check Canary Deployments",
        replace_existing=True
    )
    logger.info("Scheduled: Check canary deployments (daily at 5 AM)")
    
    # Interventions Jobs (Phase 5.4)
    
    # Every 15 minutes: Watch for invariant/gate failures
    scheduler.add_job(
        job_watch_incidents,
        trigger=CronTrigger(minute="*/15"),
        id="watch_incidents",
        name="Watch for Incidents",
        replace_existing=True
    )
    logger.info("Scheduled: Watch for incidents (every 15 minutes)")
    
    # Start scheduler
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started successfully")
    else:
        logger.info("Scheduler already running")


def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")


# ============================================================================
# Manual Job Triggers (for testing/debugging)
# ============================================================================

def run_job_now(job_id: str):
    """Manually trigger a scheduled job.
    
    Args:
        job_id: Job identifier (e.g., 'load_labeled_data')
    """
    job = scheduler.get_job(job_id)
    
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    logger.info(f"Manually triggering job: {job_id}")
    job.func()


def list_scheduled_jobs():
    """List all scheduled jobs with their next run times."""
    jobs = scheduler.get_jobs()
    
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        }
        for job in jobs
    ]
