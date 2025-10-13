"""
Grouped unsubscribe router - batch unsubscribe operations by sender domain.

Provides UX for bulk unsubscribing from multiple emails from the same sender.
"""

from collections import defaultdict
from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])


class UnsubCandidate(BaseModel):
    """Single email candidate for unsubscribe."""

    email_id: str
    sender_domain: str
    headers: Dict[str, str]


class GroupedPreview(BaseModel):
    """Preview of unsubscribe candidates grouped by sender domain."""

    domain: str
    count: int
    email_ids: List[str]
    # params carry representative headers; execution expands per-email
    params: Dict[str, Any]


@router.post("/preview_grouped")
def preview_grouped(candidates: List[UnsubCandidate]) -> Dict[str, Any]:
    """
    Group unsubscribe candidates by sender domain.

    Returns preview of how many emails per domain can be unsubscribed.

    Args:
        candidates: List of emails with domain and unsubscribe headers

    Returns:
        Dictionary with groups list, each containing domain, count, and email IDs

    Example:
        POST /unsubscribe/preview_grouped
        [
          {"email_id":"e1","sender_domain":"news.example.com","headers":{"List-Unsubscribe":"..."}},
          {"email_id":"e2","sender_domain":"news.example.com","headers":{"List-Unsubscribe":"..."}}
        ]

        Response:
        {
          "groups": [
            {
              "domain": "news.example.com",
              "count": 2,
              "email_ids": ["e1", "e2"],
              "params": {"headers": {...}}
            }
          ]
        }
    """
    by_domain: Dict[str, List[UnsubCandidate]] = defaultdict(list)

    for c in candidates:
        if c.sender_domain:
            by_domain[c.sender_domain].append(c)

    groups: List[GroupedPreview] = []
    for dom, items in by_domain.items():
        # Pick the first candidate's headers as representative
        rep = items[0]
        groups.append(
            GroupedPreview(
                domain=dom,
                count=len(items),
                email_ids=[x.email_id for x in items],
                params={"headers": rep.headers},
            )
        )

    return {"groups": [g.dict() for g in groups]}


class ExecuteGroup(BaseModel):
    """Execute unsubscribe for a group of emails from same domain."""

    domain: str
    email_ids: List[str]
    params: Dict[str, Any]  # includes headers


@router.post("/execute_grouped")
def execute_grouped(payload: ExecuteGroup):
    """
    Execute unsubscribe for all emails in a domain group.

    Fans out to individual unsubscribe executions for each email.

    Args:
        payload: Domain group with email IDs and unsubscribe headers

    Returns:
        Number of emails unsubscribed and domain name

    Example:
        POST /unsubscribe/execute_grouped
        {
          "domain": "news.example.com",
          "email_ids": ["e1", "e2"],
          "params": {"headers": {"List-Unsubscribe": "..."}}
        }

        Response:
        {
          "applied": 2,
          "domain": "news.example.com"
        }
    """
    # Fan-out to /unsubscribe/execute for each email id
    from app.routers.unsubscribe import \
        execute_unsubscribe  # reuse existing logic

    applied = 0
    for eid in payload.email_ids:
        try:
            execute_unsubscribe(
                {"email_id": eid, "headers": payload.params.get("headers", {})}
            )
            applied += 1
        except Exception as e:
            # Log but continue with other emails
            print(f"Failed to unsubscribe {eid}: {e}")

    return {"applied": applied, "domain": payload.domain}
