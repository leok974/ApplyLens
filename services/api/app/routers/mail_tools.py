"""
Mail action tools API

Provides endpoints for:
- Previewing automated actions (dry-run with safety checks)
- Executing approved actions (archive, label, quarantine, etc.)
- Tracking action history via actions_audit table

All actions are logged for transparency and debugging.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Email, ActionsAudit
from app.logic.policy import PolicyEngine, create_default_engine

router = APIRouter(prefix="/mail", tags=["mail-tools"])


class Action(BaseModel):
    """
    Represents an action to take on an email
    """
    email_id: str = Field(..., description="Email ID to act on")
    action: str = Field(..., description="Action type: label|archive|move|unsubscribe|quarantine|calendar|task|block|delete")
    params: Optional[Dict[str, Any]] = Field(None, description="Action-specific parameters (e.g., {\"label\": \"important\"})")
    policy_id: Optional[str] = Field(None, description="Policy that triggered this action")
    confidence: Optional[float] = Field(None, description="Confidence score 0-1")
    rationale: Optional[str] = Field(None, description="Human-readable explanation")
    
    class Config:
        schema_extra = {
            "example": {
                "email_id": "email_123",
                "action": "archive",
                "policy_id": "promo-expired-archive",
                "confidence": 0.85,
                "rationale": "Expired promotion (expires_at < now)"
            }
        }


class ActionPreviewResult(BaseModel):
    """
    Result of previewing an action (dry-run)
    """
    email_id: str
    allowed: bool
    explain: str
    warnings: List[str] = []
    
    class Config:
        schema_extra = {
            "example": {
                "email_id": "email_123",
                "allowed": True,
                "explain": "Expired promotion - safe to archive",
                "warnings": []
            }
        }


class ActionExecuteResult(BaseModel):
    """
    Result of executing actions
    """
    applied: int
    failed: int
    results: List[Dict[str, Any]]
    
    class Config:
        schema_extra = {
            "example": {
                "applied": 5,
                "failed": 0,
                "results": [
                    {"email_id": "email_123", "status": "success", "action": "archive"}
                ]
            }
        }


# Guardrails: Actions that require extra confirmation
HIGH_RISK_ACTIONS = {"delete", "block", "quarantine"}

# Actions that are generally safe
SAFE_ACTIONS = {"label", "archive", "move"}


def check_action_safety(action: Action, email: Optional[Email] = None) -> tuple[bool, str, List[str]]:
    """
    Apply safety checks to an action
    
    Returns:
        (allowed: bool, explanation: str, warnings: List[str])
    """
    warnings = []
    
    # Check 1: Confidence threshold
    if action.confidence and action.confidence < 0.5:
        return False, f"Confidence too low ({action.confidence:.2f} < 0.5)", warnings
    
    # Check 2: High-risk actions need high confidence
    if action.action in HIGH_RISK_ACTIONS:
        if not action.confidence or action.confidence < 0.8:
            return False, f"High-risk action '{action.action}' requires confidence >= 0.8", warnings
        warnings.append(f"High-risk action: {action.action}")
    
    # Check 3: Email exists (if provided)
    if email is None:
        warnings.append("Email not found in database - action may fail during execution")
    
    # Check 4: Action-specific validation
    if action.action == "label" and not action.params:
        return False, "Label action requires params with 'label' key", warnings
    
    if action.action == "move" and not action.params:
        return False, "Move action requires params with 'folder' key", warnings
    
    # Check 5: Rationale required for high-risk actions
    if action.action in HIGH_RISK_ACTIONS and not action.rationale:
        return False, f"High-risk action '{action.action}' requires rationale", warnings
    
    # All checks passed
    explanation = action.rationale or f"Action '{action.action}' approved"
    return True, explanation, warnings


@router.post("/actions/preview", response_model=Dict[str, Any])
async def preview_actions(
    actions: List[Action],
    db: AsyncSession = Depends(get_db)
):
    """
    Preview actions before execution (dry-run with safety checks)
    
    This endpoint:
    - Validates each action
    - Applies safety guardrails
    - Returns what would happen WITHOUT making changes
    
    Use this to show users what the automation will do.
    """
    results = []
    
    for action in actions:
        # Fetch email from database
        stmt = select(Email).where(Email.id == action.email_id)
        result = await db.execute(stmt)
        email = result.scalar_one_or_none()
        
        # Run safety checks
        allowed, explain, warnings = check_action_safety(action, email)
        
        results.append(ActionPreviewResult(
            email_id=action.email_id,
            allowed=allowed,
            explain=explain,
            warnings=warnings
        ))
    
    return {
        "count": len(actions),
        "results": [r.dict() for r in results],
        "summary": {
            "allowed": sum(1 for r in results if r.allowed),
            "blocked": sum(1 for r in results if not r.allowed),
        }
    }


@router.post("/actions/execute", response_model=ActionExecuteResult)
async def execute_actions(
    actions: List[Action],
    actor: str = "agent",  # "agent" or "user"
    db: AsyncSession = Depends(get_db)
):
    """
    Execute approved actions on emails
    
    This endpoint:
    - Re-validates actions (same safety checks as preview)
    - Applies approved actions
    - Logs everything to actions_audit table
    - Returns results
    
    IMPORTANT: This makes real changes! Use preview first.
    
    Args:
        actions: List of actions to execute
        actor: Who is taking the action ("agent" for automation, "user" for manual)
    """
    applied = 0
    failed = 0
    results_list = []
    
    for action in actions:
        try:
            # Fetch email
            stmt = select(Email).where(Email.id == action.email_id)
            result = await db.execute(stmt)
            email = result.scalar_one_or_none()
            
            # Safety check
            allowed, explain, warnings = check_action_safety(action, email)
            
            if not allowed:
                failed += 1
                results_list.append({
                    "email_id": action.email_id,
                    "status": "blocked",
                    "action": action.action,
                    "reason": explain
                })
                continue
            
            # Execute action (stubbed for now - implement actual Gmail API calls)
            action_result = await _execute_single_action(action, email, db)
            
            # Log to audit table
            audit_entry = ActionsAudit(
                email_id=action.email_id,
                action=action.action,
                actor=actor,
                policy_id=action.policy_id,
                confidence=action.confidence,
                rationale=action.rationale,
                payload=action.params or {},
                created_at=datetime.now()
            )
            db.add(audit_entry)
            
            applied += 1
            results_list.append({
                "email_id": action.email_id,
                "status": "success",
                "action": action.action,
                "explain": explain
            })
            
        except Exception as e:
            failed += 1
            results_list.append({
                "email_id": action.email_id,
                "status": "error",
                "action": action.action,
                "error": str(e)
            })
    
    # Commit all audit logs
    await db.commit()
    
    return ActionExecuteResult(
        applied=applied,
        failed=failed,
        results=results_list
    )


async def _execute_single_action(action: Action, email: Optional[Email], db: AsyncSession) -> bool:
    """
    Execute a single action on an email
    
    TODO: Implement actual Gmail API integration
    For now, this is a stub that simulates the action
    
    Returns:
        True if successful, raises exception otherwise
    """
    if action.action == "archive":
        # TODO: Call Gmail API to archive email
        # gmail_service.archive_message(email.gmail_message_id)
        pass
    
    elif action.action == "label":
        # TODO: Call Gmail API to add label
        # gmail_service.add_label(email.gmail_message_id, action.params["label"])
        pass
    
    elif action.action == "quarantine":
        # TODO: Move to quarantine folder or add quarantine label
        # gmail_service.add_label(email.gmail_message_id, "QUARANTINE")
        pass
    
    elif action.action == "delete":
        # TODO: Call Gmail API to delete (move to trash)
        # gmail_service.trash_message(email.gmail_message_id)
        pass
    
    elif action.action == "unsubscribe":
        # TODO: Parse unsubscribe link and trigger it
        # unsubscribe_url = extract_unsubscribe_link(email.body_text)
        # requests.post(unsubscribe_url)
        pass
    
    else:
        raise ValueError(f"Unknown action: {action.action}")
    
    return True


@router.get("/actions/history/{email_id}")
async def get_action_history(
    email_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get action history for a specific email
    
    Returns all actions taken on this email (manual and automated)
    """
    stmt = select(ActionsAudit).where(ActionsAudit.email_id == email_id).order_by(ActionsAudit.created_at.desc())
    result = await db.execute(stmt)
    history = result.scalars().all()
    
    return {
        "email_id": email_id,
        "actions": [
            {
                "id": h.id,
                "action": h.action,
                "actor": h.actor,
                "policy_id": h.policy_id,
                "confidence": h.confidence,
                "rationale": h.rationale,
                "created_at": h.created_at.isoformat() if h.created_at else None
            }
            for h in history
        ]
    }


@router.post("/suggest-actions")
async def suggest_actions(
    email_ids: List[str],
    db: AsyncSession = Depends(get_db)
):
    """
    Use policy engine to suggest actions for given emails
    
    This is an AI assistant endpoint that:
    1. Fetches emails from database
    2. Runs them through the policy engine
    3. Returns recommended actions
    
    Users can then review and approve via /actions/execute
    """
    # Fetch emails
    stmt = select(Email).where(Email.id.in_(email_ids))
    result = await db.execute(stmt)
    emails = result.scalars().all()
    
    # Convert to dicts for policy engine
    email_dicts = [
        {
            "id": e.id,
            "category": e.category,
            "risk_score": e.risk_score,
            "expires_at": e.expires_at.isoformat() if e.expires_at else None,
            "received_at": e.received_at.isoformat() if e.received_at else None,
            "labels": e.labels or [],
            "confidence": 0.8,  # TODO: Get from classification
        }
        for e in emails
    ]
    
    # Run policy engine
    engine = create_default_engine()
    suggestions = engine.evaluate_batch(email_dicts)
    
    return {
        "count": len(suggestions),
        "suggestions": suggestions
    }
