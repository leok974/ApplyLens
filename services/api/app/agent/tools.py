"""
Agent v2 - Tool Registry

Implements core tools:
- email_search: Query ES for emails
- thread_detail: Get full thread from DB
- security_scan: Run EmailRiskAnalyzer
- applications_lookup: Map emails → job applications
- profile_stats: Get inbox analytics
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta

from app.schemas_agent import (
    ToolResult,
    EmailSearchParams,
    SecurityScanParams,
    ThreadDetailParams,
    EmailSearchResult,
    SecurityScanResult,
    ThreadDetailResult,
    DomainRiskCache,
)
from app.es import ES_URL, ES_ENABLED
from elasticsearch import AsyncElasticsearch
from app.agent.redis_cache import get_domain_risk, set_domain_risk
from app.agent.metrics import (
    mailbox_agent_tool_calls_total,
    mailbox_agent_tool_latency_seconds,
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry of available tools for the agent.

    Each tool:
    - Takes typed parameters
    - Returns ToolResult with summary + data
    - Handles errors gracefully (never crashes)
    """

    def __init__(self):
        self.tools = {
            "email_search": self._email_search,
            "thread_detail": self._thread_detail,
            "security_scan": self._security_scan,
            "applications_lookup": self._applications_lookup,
            "profile_stats": self._profile_stats,
        }

    async def execute(
        self, tool_name: str, params: Dict[str, Any], user_id: str
    ) -> ToolResult:
        """Execute a tool by name with metrics."""
        if tool_name not in self.tools:
            mailbox_agent_tool_calls_total.labels(tool=tool_name, status="error").inc()
            return ToolResult(
                tool_name=tool_name,
                status="error",
                summary=f"Unknown tool: {tool_name}",
                error_message=f"Tool '{tool_name}' not found in registry",
            )

        try:
            with mailbox_agent_tool_latency_seconds.labels(tool=tool_name).time():
                result = await self.tools[tool_name](params, user_id)

            mailbox_agent_tool_calls_total.labels(
                tool=tool_name, status=result.status
            ).inc()
            return result

        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)
            mailbox_agent_tool_calls_total.labels(tool=tool_name, status="error").inc()
            return ToolResult(
                tool_name=tool_name,
                status="error",
                summary=f"{tool_name} encountered an error",
                error_message=str(e),
            )

    async def _email_search(self, params: Dict[str, Any], user_id: str) -> ToolResult:
        """
        Search emails using Elasticsearch.

        Implements ES query with filters for labels, risk, and time window.
        Falls back to empty results on ES failure.
        """
        try:
            # Parse params
            search_params = EmailSearchParams(**params)

            # Get ES client
            if not ES_ENABLED:
                return ToolResult(
                    tool_name="email_search",
                    status="error",
                    summary="Elasticsearch not available",
                    error_message="ES is disabled",
                )

            es = AsyncElasticsearch(ES_URL)

            # Build query
            must = []
            filters = [
                # IMPORTANT: user_id is text field, use match
                {"match": {"user_id": user_id}}
            ]

            # Full-text search on subject + body, or match_all if empty
            if search_params.query_text and search_params.query_text != "*":
                must.append(
                    {
                        "multi_match": {
                            "query": search_params.query_text,
                            "fields": ["subject^3", "body_text"],
                        }
                    }
                )
            else:
                must.append({"match_all": {}})

            # Time window filter
            if search_params.time_window_days:
                since = datetime.utcnow() - timedelta(
                    days=search_params.time_window_days
                )
                filters.append({"range": {"received_at": {"gte": since.isoformat()}}})

            # Optional labels filter (only if explicitly provided)
            if search_params.labels:
                filters.append({"terms": {"labels": search_params.labels}})

            # Optional risk filter (only if explicitly provided)
            if search_params.risk_min is not None:
                filters.append(
                    {"range": {"risk_score": {"gte": search_params.risk_min}}}
                )

            es_query = {
                "query": {
                    "bool": {
                        "must": must,
                        "filter": filters,
                    }
                },
                "sort": [{"received_at": "desc"}],
                "size": search_params.max_results,
            }

            # Debug logging
            logger.info(f"email_search ES query: {es_query}")

            # Execute search
            result = await es.search(index="gmail_emails", body=es_query)

            # Parse results
            hits = result.get("hits", {}).get("hits", [])
            total_found = result.get("hits", {}).get("total", {}).get("value", 0)

            logger.info(f"email_search: total={total_found}, returned={len(hits)}")

            emails = []
            for hit in hits:
                source = hit["_source"]
                emails.append(
                    {
                        "id": source.get("gmail_id") or hit["_id"],
                        "subject": source.get("subject", ""),
                        "sender": source.get("sender", ""),
                        "received_at": source.get("received_at"),
                        "snippet": source.get("body_text", "")[:200],
                        "risk_score": source.get("risk_score", 0),
                        "labels": source.get("labels", []),
                    }
                )

            await es.close()

            summary = f"Found {total_found} emails for user {user_id}"
            if search_params.query_text:
                summary = (
                    f"Found {total_found} emails matching '{search_params.query_text}'"
                )

            return ToolResult(
                tool_name="email_search",
                status="success",
                summary=summary,
                data=EmailSearchResult(
                    emails=emails,
                    total_found=total_found,
                    query_used=search_params.query_text,
                    filters_applied=search_params.dict(),
                ).dict(),
            )

        except Exception as e:
            logger.error(f"Email search failed: {e}", exc_info=True)
            return ToolResult(
                tool_name="email_search",
                status="error",
                summary="Email search failed",
                error_message=str(e),
            )

    async def _thread_detail(self, params: Dict[str, Any], user_id: str) -> ToolResult:
        """
        Get full thread details from database.

        TODO Phase 1.1:
        - Query Postgres for thread messages
        - Include headers, body, risk_score
        - Aggregate risk signals
        """
        try:
            thread_params = ThreadDetailParams(**params)

            # TODO: Implement DB query
            return ToolResult(
                tool_name="thread_detail",
                status="success",
                summary=f"Retrieved thread {thread_params.thread_id}",
                data=ThreadDetailResult(
                    thread_id=thread_params.thread_id,
                    messages=[],
                    participants=[],
                    risk_summary={},
                ).dict(),
            )

        except Exception as e:
            return ToolResult(
                tool_name="thread_detail",
                status="error",
                summary="Thread retrieval failed",
                error_message=str(e),
            )

    async def _security_scan(self, params: Dict[str, Any], user_id: str) -> ToolResult:
        """
        Run security scan on emails using risk scores from DB.

        Uses Redis cache for domain risk to avoid recomputation.
        Checks sender domains and returns risky vs safe breakdown.
        """
        try:
            scan_params = SecurityScanParams(**params)

            # If no email_ids provided, fetch recent emails
            if not scan_params.email_ids:
                # Use email_search to get recent emails
                search_result = await self._email_search(
                    {
                        "query_text": "*",
                        "time_window_days": 7,
                        "max_results": 50,
                    },
                    user_id,
                )

                if search_result.status != "success":
                    return ToolResult(
                        tool_name="security_scan",
                        status="error",
                        summary="Failed to fetch emails for scanning",
                        error_message=search_result.error_message,
                    )

                # data is already a dict from EmailSearchResult.dict()
                emails = search_result.data.get("emails", [])
            else:
                # TODO: Fetch specific emails by IDs from DB
                emails = []

            if not emails:
                return ToolResult(
                    tool_name="security_scan",
                    status="success",
                    summary="No emails found to scan",
                    data=SecurityScanResult(
                        scanned_count=0,
                        risky_emails=[],
                        safe_emails=[],
                        domains_checked=[],
                    ).dict(),
                )

            # Simple risk scoring stub (TODO: implement proper EmailRiskAnalyzer)
            # For now, use DB risk_score if available, else assign based on sender domain

            risky_emails = []
            safe_emails = []
            domains_checked = set()

            for email in emails:
                sender = email.get("sender", "")
                if not sender:
                    continue

                # Extract domain from sender
                domain = sender.split("@")[-1] if "@" in sender else sender
                domains_checked.add(domain)

                # Use DB risk_score if available
                risk_score = email.get("risk_score", 0) / 100.0  # Normalize to 0-1

                # Check Redis cache first
                cached_risk = await get_domain_risk(domain)
                if cached_risk is not None:
                    risk_score = cached_risk.risk_score
                else:
                    # Cache the domain risk for future use
                    await set_domain_risk(
                        domain,
                        DomainRiskCache(
                            domain=domain,
                            risk_score=risk_score,
                            first_seen_at=datetime.utcnow(),
                            last_seen_at=datetime.utcnow(),
                            email_count=1,
                            flags=[],
                            evidence={},
                        ),
                    )

                # Categorize email
                email_with_risk = {
                    **email,
                    "risk_score": risk_score,
                    "sender_domain": domain,
                }

                if risk_score >= 0.5:  # High risk threshold
                    risky_emails.append(email_with_risk)
                else:
                    safe_emails.append(email_with_risk)

            scanned_count = len(emails)
            risky_count = len(risky_emails)
            summary = f"Scanned {scanned_count} emails: {risky_count} risky, {scanned_count - risky_count} safe"

            return ToolResult(
                tool_name="security_scan",
                status="success",
                summary=summary,
                data=SecurityScanResult(
                    scanned_count=scanned_count,
                    risky_emails=risky_emails[:10],  # Limit to top 10 risky
                    safe_emails=safe_emails[:5],  # Show 5 safe samples
                    domains_checked=list(domains_checked),
                ).dict(),
            )

        except Exception as e:
            logger.error(f"Security scan failed: {e}", exc_info=True)
            return ToolResult(
                tool_name="security_scan",
                status="error",
                summary="Security scan failed",
                error_message=str(e),
            )

    async def _applications_lookup(
        self, params: Dict[str, Any], user_id: str
    ) -> ToolResult:
        """
        Map emails to job applications.

        TODO Phase 1.1:
        - Query applications table
        - Match by email_id or sender domain
        - Return application cards
        """
        try:
            # TODO: Implement applications lookup
            return ToolResult(
                tool_name="applications_lookup",
                status="success",
                summary="Found 0 related applications",
                data={"applications": []},
            )

        except Exception as e:
            return ToolResult(
                tool_name="applications_lookup",
                status="error",
                summary="Applications lookup failed",
                error_message=str(e),
            )

    async def _profile_stats(self, params: Dict[str, Any], user_id: str) -> ToolResult:
        """
        Get inbox analytics/stats.

        TODO Phase 1.1:
        - Use existing /emails/stats endpoint
        - Group by sender, label, risk_bucket
        - Return summary stats
        """
        try:
            # TODO: Implement profile stats
            return ToolResult(
                tool_name="profile_stats",
                status="success",
                summary="Retrieved inbox statistics",
                data={"stats": {}},
            )

        except Exception as e:
            return ToolResult(
                tool_name="profile_stats",
                status="error",
                summary="Profile stats failed",
                error_message=str(e),
            )


# ============================================================================
# Tool Utilities
# ============================================================================


def build_es_query(
    query_text: str,
    time_window_days: int,
    labels: Optional[List[str]] = None,
    risk_min: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Build Elasticsearch query from parameters.

    TODO Phase 1.1: Implement proper ES query builder
    """
    must = []
    filters = []

    # Text query
    if query_text and query_text != "*":
        must.append(
            {
                "multi_match": {
                    "query": query_text,
                    "fields": ["subject^2", "body", "sender"],
                    "type": "best_fields",
                }
            }
        )

    # Time window
    since = datetime.utcnow() - timedelta(days=time_window_days)
    filters.append({"range": {"received_at": {"gte": since.isoformat()}}})

    # Labels
    if labels:
        filters.append({"terms": {"labels": labels}})

    # Risk threshold
    if risk_min is not None:
        filters.append({"range": {"risk_score": {"gte": risk_min}}})

    return {
        "query": {
            "bool": {
                "must": must if must else [{"match_all": {}}],
                "filter": filters,
            }
        },
        "sort": [{"received_at": "desc"}],
        "size": 100,
    }
