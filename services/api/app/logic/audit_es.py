"""
Elasticsearch Audit Logger

Writes audit trail events to actions_audit_v1 index for real-time analytics
and Kibana dashboards. Used by the approvals tray to track policy hits vs misses.
"""

import os
from typing import Dict, Any
from elasticsearch import Elasticsearch


def es_client() -> Elasticsearch:
    """Create Elasticsearch client with optional API key authentication."""
    url = os.getenv("ES_URL", "http://localhost:9200")
    api_key = os.getenv("ES_API_KEY")
    
    if api_key:
        return Elasticsearch(url, api_key=api_key)
    return Elasticsearch(url)


def emit_audit(doc: Dict[str, Any]) -> None:
    """
    Emit an audit event to Elasticsearch.
    
    Args:
        doc: Audit document with fields:
            - email_id (str): Email ID
            - action (str): Action type
            - actor (str): agent|user|system
            - policy_id (str): Policy ID that triggered action
            - confidence (float): Confidence score
            - rationale (str): Human-readable reason
            - status (str): proposed|approved|rejected|executed
            - created_at (str): ISO timestamp
            - payload (dict): Additional context
            
    Example:
        emit_audit({
            "email_id": "email_123",
            "action": "archive",
            "actor": "agent",
            "policy_id": "promo-expired-archive",
            "confidence": 0.9,
            "rationale": "expired promotion",
            "status": "proposed",
            "created_at": "2025-10-10T12:00:00Z",
            "payload": {"expires_at": "2025-10-01T00:00:00Z"}
        })
    """
    index_name = os.getenv("ES_AUDIT_INDEX", "actions_audit_v1")
    
    try:
        client = es_client()
        client.index(index=index_name, document=doc)
    except Exception as e:
        # Log error but don't crash - audit is non-critical
        print(f"Warning: Failed to emit audit event to ES: {e}")


def emit_approval_event(
    approval_id: int,
    action: str,
    status: str,
    actor: str = "user"
) -> None:
    """
    Convenience function for emitting approval/rejection events.
    
    Args:
        approval_id: ID of the approval record
        action: approval|rejection
        status: approved|rejected
        actor: Who made the decision (default: user)
    """
    import datetime as dt
    
    emit_audit({
        "email_id": str(approval_id),  # Using approval ID as email_id for tracking
        "action": action,
        "actor": actor,
        "policy_id": "-",  # No specific policy for approval actions
        "confidence": 1.0,  # User decisions are 100% confident
        "rationale": f"User {action}",
        "status": status,
        "created_at": dt.datetime.utcnow().isoformat() + "Z",
        "payload": {"approval_id": approval_id}
    })
