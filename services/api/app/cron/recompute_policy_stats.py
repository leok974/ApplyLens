"""
Recompute Policy Stats - Phase 6 Cron Job

Scheduled job to recompute precision/recall metrics for all policy stats.

Currently:
- Recomputes precision = approved / fired
- Recall is estimated (stub for now)

Future enhancements:
- Better recall estimation by tracking manual approvals outside policy flow
- Age out old stats (e.g., keep rolling 30-day window)
- Alert on policy performance degradation

Schedule: Daily at 2:15am (after ATS enrichment)
Crontab: 15 02 * * * python services/api/app/cron/recompute_policy_stats.py
"""
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db import SessionLocal
from app.models.personalization import PolicyStats


def recompute_stats():
    """
    Recompute precision for all policy stats.
    
    Precision = approved / fired
    """
    db = SessionLocal()
    
    try:
        stats = db.query(PolicyStats).all()
        
        print(f"Recomputing stats for {len(stats)} policy-user combinations...")
        
        updated = 0
        for ps in stats:
            # Recompute precision
            denom = max(1, ps.fired)
            ps.precision = ps.approved / denom
            ps.updated_at = datetime.utcnow()
            updated += 1
        
        db.commit()
        
        print(f"✓ Updated {updated} policy stats")
        return updated
    
    except Exception as e:
        print(f"✗ Error recomputing stats: {e}")
        db.rollback()
        return 0
    
    finally:
        db.close()


def main():
    """Main entry point for cron job."""
    print("=" * 60)
    print("Recompute Policy Stats - Phase 6")
    print(f"Started: {datetime.utcnow().isoformat()}")
    print("=" * 60)
    
    updated = recompute_stats()
    
    print("=" * 60)
    print(f"Completed: {datetime.utcnow().isoformat()}")
    print(f"Updated {updated} policy stats")
    print("=" * 60)
    
    return 0 if updated >= 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
