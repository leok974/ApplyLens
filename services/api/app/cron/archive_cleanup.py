"""Archive cleanup cron job for automatic lifecycle management.

This job performs two main functions:
1. Auto-archive: Move rejected applications to archived state after X days
2. Auto-delete: Permanently delete archived applications after Y days

Respects opt-out flags and includes audit logging for compliance.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple

from sqlalchemy.orm import Session

from app.config import agent_settings
from app.db import SessionLocal, audit_action
from app.models import Application, AppStatus

logger = logging.getLogger(__name__)


def run_archive_cleanup(dry_run: bool = False) -> Tuple[int, int]:
    """
    Run the archive cleanup job.
    
    Args:
        dry_run: If True, only log what would be done without making changes
        
    Returns:
        Tuple of (archived_count, deleted_count)
    """
    db: Session = SessionLocal()
    archived_count = 0
    deleted_count = 0
    
    try:
        now = datetime.now(timezone.utc)
        
        # ===== PHASE 1: Auto-archive rejected applications =====
        archive_cutoff = now - timedelta(days=agent_settings.AUTO_ARCHIVE_REJECTED_AFTER_DAYS)
        
        logger.info(
            f"[Archive Cleanup] Starting auto-archive pass "
            f"(cutoff: {archive_cutoff}, dry_run: {dry_run})"
        )
        
        # Find rejected applications older than cutoff that aren't archived/deleted
        apps_to_archive = (
            db.query(Application)
            .filter(
                Application.status == AppStatus.rejected,
                Application.updated_at < archive_cutoff,
                Application.archived_at.is_(None),
                Application.archive_opt_out.is_(False),
                Application.deleted_at.is_(None),
            )
            .all()
        )
        
        logger.info(f"[Archive Cleanup] Found {len(apps_to_archive)} applications to auto-archive")
        
        for app in apps_to_archive:
            if dry_run:
                logger.info(
                    f"[Archive Cleanup] [DRY RUN] Would archive app {app.id} "
                    f"({app.company} - {app.role}, status: {app.status}, "
                    f"updated: {app.updated_at})"
                )
            else:
                app.archived_at = now
                archived_count += 1
                
                # Audit log
                audit_action(
                    email_id=str(app.id),
                    action="application.auto_archive",
                    actor="system",
                    rationale=f"Auto-archived after {agent_settings.AUTO_ARCHIVE_REJECTED_AFTER_DAYS} days",
                )
                
                logger.info(
                    f"[Archive Cleanup] Archived app {app.id} "
                    f"({app.company} - {app.role})"
                )
                
                # Sync to Elasticsearch (tombstone)
                try:
                    from app.utils.es_applications import es_tombstone_application
                    es_tombstone_application(app.id)
                except Exception as e:
                    logger.warning(f"ES sync failed for auto-archive app {app.id}: {e}")
        
        if not dry_run and archived_count > 0:
            db.commit()
            logger.info(f"[Archive Cleanup] Successfully archived {archived_count} applications")
        
        # ===== PHASE 2: Auto-delete archived applications =====
        delete_cutoff = now - timedelta(days=agent_settings.AUTO_DELETE_ARCHIVED_AFTER_DAYS)
        
        logger.info(
            f"[Archive Cleanup] Starting auto-delete pass "
            f"(cutoff: {delete_cutoff}, dry_run: {dry_run})"
        )
        
        # Find archived applications older than cutoff that aren't deleted
        apps_to_delete = (
            db.query(Application)
            .filter(
                Application.archived_at.isnot(None),
                Application.archived_at < delete_cutoff,
                Application.auto_delete_opt_out.is_(False),
                Application.deleted_at.is_(None),
            )
            .all()
        )
        
        logger.info(f"[Archive Cleanup] Found {len(apps_to_delete)} applications to auto-delete")
        
        for app in apps_to_delete:
            if dry_run:
                logger.info(
                    f"[Archive Cleanup] [DRY RUN] Would delete app {app.id} "
                    f"({app.company} - {app.role}, archived: {app.archived_at})"
                )
            else:
                # Audit log before deletion
                audit_action(
                    email_id=str(app.id),
                    action="application.auto_delete",
                    actor="system",
                    rationale=f"Auto-deleted after {agent_settings.AUTO_DELETE_ARCHIVED_AFTER_DAYS} days archived",
                )
                
                # Sync to Elasticsearch (delete document)
                try:
                    from app.utils.es_applications import es_delete_application
                    es_delete_application(app.id)
                except Exception as e:
                    logger.warning(f"ES sync failed for auto-delete app {app.id}: {e}")
                
                # Hard delete from database
                app.deleted_at = now
                db.delete(app)
                deleted_count += 1
                
                logger.info(
                    f"[Archive Cleanup] Deleted app {app.id} "
                    f"({app.company} - {app.role})"
                )
        
        if not dry_run and deleted_count > 0:
            db.commit()
            logger.info(f"[Archive Cleanup] Successfully deleted {deleted_count} applications")
        
        # Summary
        if dry_run:
            logger.info(
                f"[Archive Cleanup] DRY RUN complete: "
                f"would archive {len(apps_to_archive)}, would delete {len(apps_to_delete)}"
            )
        else:
            logger.info(
                f"[Archive Cleanup] Job complete: "
                f"archived {archived_count}, deleted {deleted_count}"
            )
        
        return (archived_count, deleted_count)
        
    except Exception as e:
        logger.error(f"[Archive Cleanup] Job failed: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Entry point for manual/CLI execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run archive cleanup job")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - log actions without making changes"
    )
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger.info("=== Archive Cleanup Job Started ===")
    logger.info(f"Settings: archive_after={agent_settings.AUTO_ARCHIVE_REJECTED_AFTER_DAYS}d, "
                f"delete_after={agent_settings.AUTO_DELETE_ARCHIVED_AFTER_DAYS}d, "
                f"grace_period={agent_settings.ARCHIVE_GRACE_UNDO_HOURS}h")
    
    archived, deleted = run_archive_cleanup(dry_run=args.dry_run)
    
    logger.info(f"=== Archive Cleanup Job Completed: {archived} archived, {deleted} deleted ===")


if __name__ == "__main__":
    main()
