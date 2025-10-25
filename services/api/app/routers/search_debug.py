"""
Search health and debug endpoint.

Provides diagnostic information about Elasticsearch alias, index stats,
and sample documents for the current user. Useful for troubleshooting
search issues.
"""

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..deps.user import get_current_user_email
from ..es import ES_ENABLED, es

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/health", response_model=Dict[str, Any])
def search_health(user_email: str = Depends(get_current_user_email)):
    """
    Get search health diagnostics for current user.

    Returns:
    - alias: The ES index/alias being queried
    - alias_total: Total document count across all users
    - owner: Current user's email
    - owner_total: Document count for current user
    - sample: Sample document for current user (if any)

    Useful for debugging "0 results" issues.
    """
    if not ES_ENABLED or es is None:
        return {
            "status": "disabled",
            "error": "Elasticsearch is not enabled",
        }

    try:
        alias = os.getenv("ELASTICSEARCH_INDEX", "gmail_emails")

        # Total count across all users
        total_count = es.count(index=alias)["count"]

        # Count for current user
        owner_query = {"query": {"term": {"owner_email.keyword": user_email}}}
        owner_count_resp = es.count(index=alias, body=owner_query)
        owner_count = owner_count_resp["count"]

        # Get a sample document for current user
        sample_resp = es.search(
            index=alias,
            size=1,
            body={
                "query": {"term": {"owner_email.keyword": user_email}},
                "sort": [{"received_at": "desc"}],
            },
        )

        sample_hits = sample_resp.get("hits", {}).get("hits", [])
        sample = None
        if sample_hits:
            hit = sample_hits[0]
            source = hit.get("_source", {})
            sample = {
                "gmail_id": source.get("gmail_id"),
                "subject": source.get("subject"),
                "sender": source.get("sender"),
                "received_at": source.get("received_at"),
                "owner_email": source.get("owner_email"),
                "labels": source.get("labels", []),
            }

        return {
            "status": "ok",
            "alias": alias,
            "alias_total": total_count,
            "owner": user_email,
            "owner_total": owner_count,
            "sample": sample,
            "info": (
                f"Found {owner_count} emails for {user_email} out of {total_count} total"
            ),
        }

    except Exception as e:
        logger.error(f"Search health check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "owner": user_email,
        }
