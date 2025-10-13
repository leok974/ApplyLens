from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from .settings import settings
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import json

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def audit_action(
    email_id: str,
    action: str,
    actor: str = "agent",
    policy_id: Optional[str] = None,
    confidence: Optional[float] = None,
    rationale: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None
) -> None:
    """
    Insert an action audit record into the actions_audit table.
    
    Args:
        email_id: ID of the email the action was performed on
        action: Action type (archive, delete, label, unsubscribe, etc.)
        actor: Who performed the action ("agent" or "user")
        policy_id: ID of the policy that triggered this action
        confidence: Confidence score (0-1) for the action
        rationale: Human-readable explanation for the action
        payload: Additional metadata about the action (JSON)
    """
    from .models import ActionsAudit
    
    db = SessionLocal()
    try:
        audit_record = ActionsAudit(
            email_id=email_id,
            action=action,
            actor=actor,
            policy_id=policy_id,
            confidence=confidence,
            rationale=rationale,
            payload=payload,
            created_at=datetime.now(timezone.utc)
        )
        db.add(audit_record)
        db.commit()
    except Exception as e:
        db.rollback()
        # Log error but don't crash
        print(f"Error auditing action: {e}")
    finally:
        db.close()


# ============================================================================
# Approvals Tray Functions
# ============================================================================


def approvals_bulk_insert(rows: List[Dict[str, Any]]) -> None:
    """
    Bulk insert proposed actions into approvals_proposed table.
    
    Args:
        rows: List of approval records with email_id, action, policy_id, 
              confidence, rationale (optional), params (optional)
    """
    db = SessionLocal()
    try:
        for row in rows:
            params_json = json.dumps(row.get("params") or {})
            db.execute(
                text("""
                    INSERT INTO approvals_proposed
                    (email_id, action, policy_id, confidence, rationale, params, status)
                    VALUES (:email_id, :action, :policy_id, :confidence, :rationale, 
                            cast(:params as jsonb), 'proposed')
                """),
                {
                    "email_id": row["email_id"],
                    "action": row["action"],
                    "policy_id": row["policy_id"],
                    "confidence": row["confidence"],
                    "rationale": row.get("rationale", ""),
                    "params": params_json,
                }
            )
        db.commit()
    except Exception as e:
        db.rollback()
        raise Exception(f"Error inserting approvals: {e}")
    finally:
        db.close()


def approvals_get(status: str = "proposed", limit: int = 200) -> List[Dict[str, Any]]:
    """
    Get approval records by status.
    
    Args:
        status: Filter by status (proposed, approved, rejected, executed)
        limit: Maximum number of records to return
        
    Returns:
        List of approval records as dictionaries
    """
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT id, email_id, action, policy_id, confidence, rationale, 
                       params, status, created_at
                FROM approvals_proposed 
                WHERE status = :status
                ORDER BY created_at DESC 
                LIMIT :limit
            """),
            {"status": status, "limit": limit}
        )
        
        columns = result.keys()
        rows = []
        for row in result:
            row_dict = dict(zip(columns, row))
            # Parse JSONB params back to dict
            if row_dict.get("params"):
                try:
                    row_dict["params"] = json.loads(row_dict["params"]) if isinstance(row_dict["params"], str) else row_dict["params"]
                except:
                    pass
            rows.append(row_dict)
        
        return rows
    finally:
        db.close()


def approvals_update_status(ids: List[int], status: str) -> None:
    """
    Update status for multiple approval records.
    
    Args:
        ids: List of approval record IDs to update
        status: New status (approved, rejected, executed)
    """
    db = SessionLocal()
    try:
        db.execute(
            text("""
                UPDATE approvals_proposed 
                SET status = :status, updated_at = now() 
                WHERE id = ANY(:ids)
            """),
            {"status": status, "ids": ids}
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise Exception(f"Error updating approval status: {e}")
    finally:
        db.close()
