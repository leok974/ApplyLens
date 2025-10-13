"""
Policy Execution Router

Endpoint for running policy sets against email collections and generating
proposed actions for approval. This creates the "approvals tray" workflow.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import datetime as dt

from app.logic.search import find_by_filter
from app.logic.policy_engine import apply_policies, ProposedAction

router = APIRouter(prefix="/policies", tags=["policies"])


class PolicySet(BaseModel):
    """A named collection of policies."""

    id: str
    policies: List[Dict[str, Any]]


class PolicyRunRequest(BaseModel):
    """Request to run a policy set against an email collection."""

    policy_set: PolicySet
    es_filter: Dict[str, Any]  # Full ES DSL query (e.g., {"bool":{"filter":[...]}})
    limit: Optional[int] = 300


class PolicyRunResponse(BaseModel):
    """Response containing proposed actions for approval."""

    policy_set_id: str
    evaluated: int
    proposed_actions: List[Dict[str, Any]]


@router.post("/run", response_model=PolicyRunResponse)
async def run_policies(req: PolicyRunRequest):
    """
    Run a policy set against emails matching the ES filter.

    This endpoint:
    1. Queries Elasticsearch with the provided filter
    2. Applies the policy set to each matching email
    3. Returns all proposed actions for user approval

    Example request:
    ```json
    {
      "policy_set": {
        "id": "cleanup-promos",
        "policies": [{
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
      },
      "es_filter": {"term": {"category": "promotions"}},
      "limit": 300
    }
    ```

    Example response:
    ```json
    {
      "policy_set_id": "cleanup-promos",
      "evaluated": 150,
      "proposed_actions": [
        {
          "email_id": "email_123",
          "action": "archive",
          "policy_id": "promo-expired-archive",
          "confidence": 0.9,
          "rationale": "expired promotion"
        }
      ]
    }
    ```

    Args:
        req: PolicyRunRequest with policy set, ES filter, and optional limit

    Returns:
        PolicyRunResponse with evaluated count and proposed actions

    Raises:
        HTTPException: If search fails or returns invalid data
    """
    # Find emails matching the filter
    emails = await find_by_filter(req.es_filter, limit=req.limit)
    if not isinstance(emails, list):
        raise HTTPException(500, "Unexpected search result")

    # Apply policies to each email
    now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat()
    proposed: List[ProposedAction] = []

    for email in emails:
        actions = apply_policies(email, req.policy_set.policies, now_iso=now)
        proposed.extend(actions)

    # Convert ProposedAction objects to dicts for JSON response
    return PolicyRunResponse(
        policy_set_id=req.policy_set.id,
        evaluated=len(emails),
        proposed_actions=[action.__dict__ for action in proposed],
    )
