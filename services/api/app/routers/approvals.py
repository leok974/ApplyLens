"""
Approvals Tray API

Workflow for policy-based email automation with human approval:
1. POST /approvals/propose - Policy engine proposes actions
2. GET /approvals/proposed - List proposed actions for review
3. POST /approvals/approve - Approve selected actions
4. POST /approvals/reject - Reject selected actions
5. POST /approvals/execute - Execute approved actions

All actions are mirrored to Elasticsearch (actions_audit_v1) for analytics.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import datetime as dt

from app.db import (
    approvals_bulk_insert,
    approvals_get,
    approvals_update_status,
)
from app.logic.audit_es import emit_audit

router = APIRouter(prefix="/approvals", tags=["approvals"])


# ============================================================================
# Request/Response Models
# ============================================================================


class Proposed(BaseModel):
    """A single proposed action from policy engine."""

    email_id: str
    action: str
    policy_id: str
    confidence: float
    rationale: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class BulkPropose(BaseModel):
    """Bulk propose multiple actions."""

    items: List[Proposed]


class ApproveReject(BaseModel):
    """Approve or reject actions by ID."""

    ids: List[int]


class ExecuteRequest(BaseModel):
    """Execute approved actions."""

    items: List[Proposed]


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/propose")
def propose(payload: BulkPropose):
    """
    Propose actions for approval (from policy engine).

    This endpoint receives proposed actions from the policy engine
    (/policies/run) and stores them for user review. All proposals
    are written to both Postgres and Elasticsearch for tracking.

    Args:
        payload: List of proposed actions with email_id, action, policy_id, etc.

    Returns:
        {"accepted": count} - Number of proposals stored

    Example:
        POST /approvals/propose
        {
          "items": [
            {
              "email_id": "email_123",
              "action": "archive",
              "policy_id": "promo-expired-archive",
              "confidence": 0.9,
              "rationale": "expired promotion"
            }
          ]
        }
    """
    if not payload.items:
        raise HTTPException(400, "No items provided")

    # Convert to dict for DB insert
    rows = [item.model_dump() for item in payload.items]

    # Insert into Postgres
    try:
        approvals_bulk_insert(rows)
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

    # Mirror to Elasticsearch audit trail
    now = dt.datetime.utcnow().isoformat() + "Z"
    for row in rows:
        emit_audit(
            {
                "email_id": row["email_id"],
                "action": row["action"],
                "actor": "agent",
                "policy_id": row["policy_id"],
                "confidence": row["confidence"],
                "rationale": row.get("rationale", ""),
                "status": "proposed",
                "created_at": now,
                "payload": row.get("params") or {},
            }
        )

    return {"accepted": len(rows)}


@router.get("/proposed")
def list_proposed(limit: int = 200):
    """
    List proposed actions awaiting approval.

    Returns all actions with status='proposed' sorted by creation time.

    Args:
        limit: Maximum number of records to return (default: 200)

    Returns:
        {"items": [...]} - List of proposed actions

    Example:
        GET /approvals/proposed?limit=50

        Response:
        {
          "items": [
            {
              "id": 1,
              "email_id": "email_123",
              "action": "archive",
              "policy_id": "promo-expired-archive",
              "confidence": 0.9,
              "rationale": "expired promotion",
              "params": {},
              "status": "proposed",
              "created_at": "2025-10-10T12:00:00Z"
            }
          ]
        }
    """
    items = approvals_get(status="proposed", limit=limit)
    return {"items": items}


@router.post("/approve")
def approve(payload: ApproveReject):
    """
    Approve selected actions.

    Changes status from 'proposed' to 'approved' for the given IDs.
    Approved actions can then be executed via /approvals/execute.

    Args:
        payload: List of approval record IDs to approve

    Returns:
        {"updated": count, "status": "approved"}

    Example:
        POST /approvals/approve
        {
          "ids": [1, 2, 3]
        }
    """
    if not payload.ids:
        raise HTTPException(400, "No IDs provided")

    try:
        approvals_update_status(payload.ids, "approved")
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

    # Mirror to ES audit trail
    for approval_id in payload.ids:
        emit_audit(
            {
                "email_id": str(approval_id),
                "action": "approval",
                "actor": "user",
                "policy_id": "-",
                "confidence": 1.0,
                "rationale": "User approved",
                "status": "approved",
                "created_at": dt.datetime.utcnow().isoformat() + "Z",
                "payload": {"approval_id": approval_id},
            }
        )

    return {"updated": len(payload.ids), "status": "approved"}


@router.post("/reject")
def reject(payload: ApproveReject):
    """
    Reject selected actions.

    Changes status from 'proposed' to 'rejected' for the given IDs.
    Rejected actions will not be executed.

    Args:
        payload: List of approval record IDs to reject

    Returns:
        {"updated": count, "status": "rejected"}

    Example:
        POST /approvals/reject
        {
          "ids": [4, 5]
        }
    """
    if not payload.ids:
        raise HTTPException(400, "No IDs provided")

    try:
        approvals_update_status(payload.ids, "rejected")
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

    # Mirror to ES audit trail
    for approval_id in payload.ids:
        emit_audit(
            {
                "email_id": str(approval_id),
                "action": "rejection",
                "actor": "user",
                "policy_id": "-",
                "confidence": 1.0,
                "rationale": "User rejected",
                "status": "rejected",
                "created_at": dt.datetime.utcnow().isoformat() + "Z",
                "payload": {"approval_id": approval_id},
            }
        )

    return {"updated": len(payload.ids), "status": "rejected"}


@router.post("/execute")
async def execute(payload: ExecuteRequest):
    """
    Execute approved actions.

    This endpoint executes the approved actions by calling the appropriate
    action executors (mail_tools, unsubscribe, etc.). Actions are split
    by type and routed to the correct executor.

    Args:
        payload: List of approved actions to execute

    Returns:
        {"applied": count} - Number of actions successfully executed

    Example:
        POST /approvals/execute
        {
          "items": [
            {
              "email_id": "email_123",
              "action": "archive",
              "policy_id": "promo-expired-archive",
              "confidence": 0.9,
              "rationale": "expired promotion",
              "params": {}
            }
          ]
        }
    """
    if not payload.items:
        return {"applied": 0}

    # Split by action type for routing
    mail_actions = []
    unsub_actions = []

    for item in payload.items:
        if item.action == "unsubscribe":
            unsub_actions.append(item)
        else:
            mail_actions.append(item)

    applied = 0

    # Execute mail actions (archive, delete, label, etc.)
    if mail_actions:
        try:
            # Import here to avoid circular dependencies
            from app.routers.mail_tools import execute_actions_internal

            # Convert to expected format
            actions_payload = [
                {
                    "email_id": item.email_id,
                    "action": item.action,
                    "policy_id": item.policy_id,
                    "confidence": item.confidence,
                    "rationale": item.rationale,
                    "params": item.params or {},
                }
                for item in mail_actions
            ]

            result = await execute_actions_internal(actions_payload)
            applied += result.get("applied", 0)
        except Exception as e:
            print(f"Error executing mail actions: {e}")

    # Execute unsubscribe actions
    if unsub_actions:
        try:
            # Import here to avoid circular dependencies
            from app.logic.unsubscribe import perform_unsubscribe

            for item in unsub_actions:
                headers = (item.params or {}).get("headers", {})
                if headers:
                    try:
                        await perform_unsubscribe(headers)
                        applied += 1
                    except Exception as e:
                        print(f"Error unsubscribing {item.email_id}: {e}")
        except Exception as e:
            print(f"Error executing unsubscribe actions: {e}")

    # Audit all executed actions to ES
    now = dt.datetime.utcnow().isoformat() + "Z"
    for item in payload.items:
        emit_audit(
            {
                "email_id": item.email_id,
                "action": item.action,
                "actor": "agent",
                "policy_id": item.policy_id,
                "confidence": item.confidence,
                "rationale": item.rationale or "",
                "status": "executed",
                "created_at": now,
                "payload": item.params or {},
            }
        )

    return {"applied": applied}
