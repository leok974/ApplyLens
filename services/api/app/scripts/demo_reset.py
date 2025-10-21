"""
Nightly: wipe & reseed the demo tenant then re-index ES.
Run via cron/Task Scheduler or a small sidecar container.

Usage:
  python -m app.scripts.demo_reset
"""
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import User, Email, Application
from app.utils.es_applications import es_upsert_application, es_delete_application
from datetime import datetime, timezone
import json
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEMO_EMAIL = "demo@applylens.app"
SEED_PATH = os.getenv("DEMO_SEED_PATH", "/app/seeds/demo_seed.json")


def run():
    """Reset demo user data with fresh seed."""
    logger.info("🔄 Starting demo reset...")
    
    try:
        with SessionLocal() as db:
            # Find or create demo user
            demo = db.query(User).filter_by(email=DEMO_EMAIL).first()
            if not demo:
                logger.info(f"Creating demo user: {DEMO_EMAIL}")
                demo = User(
                    email=DEMO_EMAIL,
                    name="Demo User",
                    is_demo=True
                )
                db.add(demo)
                db.commit()
                db.refresh(demo)
            else:
                logger.info(f"Found existing demo user: {DEMO_EMAIL}")

            # Get existing app IDs before deletion (for ES cleanup)
            # NOTE: This is a single-user system, so we delete ALL data
            existing_app_ids = [app.id for app in db.query(Application).all()]
            
            # Clear ALL previous data (single-user mode)
            logger.info("🗑️  Clearing ALL existing data (single-user mode)...")
            deleted_emails = db.query(Email).delete()
            deleted_apps = db.query(Application).delete()
            db.commit()
            logger.info(f"Deleted {deleted_emails} emails and {deleted_apps} applications")

            # Delete from Elasticsearch
            for app_id in existing_app_ids:
                try:
                    es_delete_application(app_id)
                except Exception as ex:
                    logger.warning(f"ES delete failed for app {app_id}: {ex}")

            # Load seed data
            logger.info(f"📂 Loading seed from {SEED_PATH}")
            if not os.path.exists(SEED_PATH):
                logger.error(f"Seed file not found: {SEED_PATH}")
                return
                
            with open(SEED_PATH, 'r', encoding='utf-8') as f:
                seed = json.load(f)

            # Insert applications
            logger.info("📝 Seeding applications...")
            apps = []
            for a in seed.get('applications', []):
                # Application model doesn't have user_id, owner_email, applied_at, location
                # It's a single-user system
                
                app = Application(
                    company=a['company'],
                    role=a['role'],
                    status=a['status'],
                    notes=a.get('notes')
                )
                db.add(app)
                apps.append(app)
            
            db.commit()
            logger.info(f"Created {len(apps)} applications")

            # Insert emails
            logger.info("📧 Seeding emails...")
            email_count = 0
            for e in seed.get('emails', []):
                # Parse received_at if it's a string
                received_at = e.get('received_at')
                if isinstance(received_at, str):
                    received_at = datetime.fromisoformat(received_at.replace('Z', '+00:00'))
                
                # Email model uses owner_email, not user_id
                email = Email(
                    owner_email=DEMO_EMAIL,
                    subject=e.get('subject'),
                    sender=e.get('from_email'),
                    received_at=received_at,
                    labels=e.get('labels', []),
                    body_text=e.get('body_text'),
                    raw={'snippet': e.get('snippet')}
                )
                db.add(email)
                email_count += 1
            
            db.commit()
            logger.info(f"Created {email_count} emails")

            # Re-index applications in Elasticsearch
            logger.info("🔍 Re-indexing applications in Elasticsearch...")
            for app in apps:
                try:
                    db.refresh(app)  # Ensure we have latest data with IDs
                    es_upsert_application(app)
                except Exception as ex:
                    logger.warning(f"ES upsert failed for {app.company}: {ex}")

            logger.info("✅ Demo reset completed successfully")
            
    except Exception as e:
        logger.error(f"❌ Demo reset failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
