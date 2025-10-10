"""
Natural Language Agent Router

Provides an endpoint for parsing natural language commands and routing them
to appropriate email automation actions.

Supports commands like:
- "clean my promos older than 7 days"
- "unsubscribe from newsletters I haven't opened in 60 days"
- "show me suspicious emails"
- "summarize bills due before next week"
- "show my bills due before Friday"
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
import re
import datetime as dt

# Import search helpers and policy engine
from app.logic.search import (
    find_expired_promos,
    find_high_risk,
    find_unsubscribe_candidates,
    find_bills_due_before,
)
from app.logic.policy_engine import apply_policies
from app.logic.timewin import parse_due_cutoff
from app.routers.productivity import (
    CreateRemindersRequest,
    Reminder,
    create_reminders,
)

router = APIRouter(prefix="/nl", tags=["nl-agent"])


class NLQuery(BaseModel):
    """Natural language query from user."""
    text: str


def intent_and_params(text: str) -> Dict[str, Any]:
    """
    Parse natural language text to extract intent and parameters.
    
    This is a simple rule-based parser. Can be upgraded to LLM-based
    parsing for more sophisticated intent recognition.
    
    Args:
        text: Natural language command from user
        
    Returns:
        Dictionary with "intent" and extracted parameters
        
    Supported intents:
    - clean_promos: Archive expired promotional emails
    - unsubscribe_stale: Unsubscribe from inactive senders
    - show_suspicious: Show high-risk emails
    - summarize_bills: Summarize upcoming bills
    - fallback: Unrecognized command
        
    Examples:
        intent_and_params("clean my promos older than 7 days")
        # Returns: {"intent": "clean_promos", "days": 7}
        
        intent_and_params("unsubscribe from newsletters I haven't opened in 60 days")
        # Returns: {"intent": "unsubscribe_stale", "days": 60}
        
        intent_and_params("show me suspicious emails")
        # Returns: {"intent": "show_suspicious"}
    """
    t = text.lower()
    
    # Clean/archive expired promotions
    if "clean" in t and "promo" in t:
        days = 7  # default
        m = re.search(r"older than (\d+)\s*day", t)
        if m:
            days = int(m.group(1))
        return {"intent": "clean_promos", "days": days}
    
    # Unsubscribe from stale senders
    if "unsubscribe" in t:
        days = 60  # default
        m = re.search(r"(\d+)\s*day", t)
        if m:
            days = int(m.group(1))
        return {"intent": "unsubscribe_stale", "days": days}
    
    # Show suspicious/high-risk emails
    if any(word in t for word in ["suspicious", "fishy", "malware", "phish", "spam", "risky"]):
        return {"intent": "show_suspicious"}
    
    # Summarize bills
    if "bills" in t and ("due" in t or "before" in t):
        # Simple: summarize by date filter
        return {"intent": "summarize_bills", "before": None}
    
    # Fallback for unrecognized commands
    return {"intent": "fallback"}


@router.post("/run")
async def run(query: NLQuery):
    """
    Execute a natural language command.
    
    Parses the user's text, identifies the intent, and routes to the
    appropriate email automation action. Returns proposed actions that
    can be previewed or executed.
    
    Args:
        query: NLQuery with text command
        
    Returns:
        Dictionary with:
        - intent: Identified intent
        - proposed_actions: List of actions to take (if applicable)
        - emails: List of matching emails (if applicable)
        - count: Number of results
        - message: Help text (for fallback)
        
    Examples:
        POST /nl/run
        {"text": "clean my promos older than 7 days"}
        
        Response:
        {
            "intent": "clean_promos",
            "proposed_actions": [
                {
                    "email_id": "msg123",
                    "action": "archive",
                    "policy_id": "promo-expired-archive",
                    "confidence": 0.8,
                    "rationale": "expired promotion"
                }
            ],
            "count": 1
        }
    """
    # Parse intent and parameters
    parsed = intent_and_params(query.text)
    now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat()
    
    # Route to appropriate handler
    if parsed["intent"] == "clean_promos":
        # Find expired promotional emails
        emails = await find_expired_promos(days=parsed["days"])
        
        # Define policy for archiving expired promos
        policies = [{
            "id": "promo-expired-archive",
            "if": {
                "all": [
                    {"field": "category", "op": "=", "value": "promotions"},
                    {"field": "expires_at", "op": "<", "value": "now"}
                ]
            },
            "then": {
                "action": "archive",
                "confidence_min": 0.8,
                "rationale": "expired promotion"
            }
        }]
        
        # Apply policies to generate actions
        actions = []
        for e in emails:
            proposed = apply_policies(e, policies, now_iso=now)
            actions.extend([a.__dict__ for a in proposed])
        
        return {
            "intent": "clean_promos",
            "proposed_actions": actions,
            "count": len(actions)
        }
    
    elif parsed["intent"] == "unsubscribe_stale":
        # Find emails from stale senders
        emails = await find_unsubscribe_candidates(days=parsed["days"])
        
        # Create unsubscribe action proposals
        # These can be approved and executed via /unsubscribe/execute endpoint
        acts = [
            {
                "email_id": e["id"],
                "action": "unsubscribe",
                "policy_id": "unsubscribe-stale",
                "confidence": 0.9,
                "rationale": f"no opens in {parsed['days']}d"
            }
            for e in emails
        ]
        
        return {
            "intent": "unsubscribe_stale",
            "proposed_actions": acts,
            "count": len(acts)
        }
    
    elif parsed["intent"] == "show_suspicious":
        # Find high-risk emails
        emails = await find_high_risk()
        
        return {
            "intent": "show_suspicious",
            "emails": emails,
            "count": len(emails)
        }
    
    elif parsed["intent"] == "summarize_bills":
        # Parse date cutoff from natural language
        cutoff = parse_due_cutoff(query.text)
        
        # Find bills due before cutoff
        emails = []
        if cutoff:
            emails = await find_bills_due_before(cutoff_iso=cutoff)
        
        # Build reminders for each bill email
        items = []
        for e in emails:
            # Extract due date from dates array or expires_at
            due_at = cutoff  # Default to cutoff
            if e.get("dates") and len(e["dates"]) > 0:
                due_at = e["dates"][0]  # First date in array
            elif e.get("expires_at"):
                due_at = e["expires_at"]
            
            # Format money amounts if available
            money_str = ""
            if e.get("money_amounts"):
                amounts = e["money_amounts"]
                if amounts and len(amounts) > 0:
                    amt = amounts[0]
                    money_str = f" - ${amt.get('amount', 0):.2f}"
            
            items.append({
                "email_id": e["id"],
                "title": (e.get("subject") or f"Bill from {e.get('sender_domain', 'unknown')}") + money_str,
                "due_at": due_at,
                "notes": f"Auto-created from bills due search (category: {e.get('category')})"
            })
        
        # Fallback if no bills found
        if not items:
            items = [{
                "email_id": "bill_fallback",
                "title": "No bills found" + (f" before {cutoff}" if cutoff else ""),
                "due_at": cutoff,
                "notes": "Try specifying a date like 'before Friday' or 'by 10/15'"
            }]
        
        # Create reminders via productivity router
        reminder_req = CreateRemindersRequest(
            items=[Reminder(**item) for item in items]
        )
        created = create_reminders(reminder_req)
        
        return {
            "intent": "summarize_bills",
            "cutoff": cutoff,
            "created": created["created"],
            "reminders": items,
            "count": len(emails)
        }
    
    # Fallback for unrecognized commands
    return {
        "intent": "fallback",
        "message": (
            "I didn't understand that command. Try:\n"
            "- 'clean promos older than 7 days'\n"
            "- 'unsubscribe from newsletters I haven't opened in 60 days'\n"
            "- 'show suspicious emails'\n"
            "- 'summarize bills due soon'"
        )
    }
