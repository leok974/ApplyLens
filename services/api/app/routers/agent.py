"""
Agent v2 - API Router

Endpoints:
- POST /agent/mailbox/run - Execute agent run
- GET /agent/mailbox/run/{run_id} - Get run status
- GET /agent/tools - List available tools
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from app.schemas_agent import AgentRunRequest, AgentRunResponse
from app.agent.orchestrator import MailboxAgentOrchestrator

router = APIRouter(prefix="/agent", tags=["agent-v2"])
logger = logging.getLogger(__name__)

# Initialize orchestrator (singleton)
_orchestrator = None


def get_orchestrator() -> MailboxAgentOrchestrator:
    """Get or create orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MailboxAgentOrchestrator()
    return _orchestrator


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/mailbox/run", response_model=AgentRunResponse)
async def run_mailbox_agent(
    request: AgentRunRequest,
    # current_user = Depends(get_current_user)  # TODO: Enable auth
):
    """
    Execute a mailbox agent run.

    Flow:
    1. Classify intent from query
    2. Plan + execute tools
    3. Synthesize answer with LLM
    4. Return structured response with cards

    Example request:
    ```json
    {
      "query": "Show suspicious emails from new domains this week",
      "mode": "preview_only",
      "context": {
        "time_window_days": 7,
        "filters": {"labels": ["INBOX"], "risk_min": 80}
      },
      "user_id": "user@gmail.com"
    }
    ```
    """
    try:
        logger.info(
            f"Agent run requested: query='{request.query}', user={request.user_id}"
        )

        orchestrator = get_orchestrator()
        response = await orchestrator.run(request)

        logger.info(
            f"Agent run completed: run_id={response.run_id}, status={response.status}"
        )
        return response

    except Exception as e:
        logger.error(f"Agent run failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent run failed: {str(e)}")


@router.get("/mailbox/run/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(run_id: str):
    """
    Get agent run by ID.

    TODO Phase 1.2: Store runs in DB/Redis for retrieval
    For now, returns 404 (runs not persisted yet)
    """
    raise HTTPException(
        status_code=404,
        detail="Run history not implemented yet. Runs are not persisted.",
    )


@router.get("/tools")
async def list_tools() -> Dict[str, Any]:
    """
    List available tools for the agent.

    Returns tool metadata for UI/debugging.
    """
    tools_info = {
        "email_search": {
            "name": "Email Search",
            "description": "Search emails using Elasticsearch",
            "parameters": [
                "query_text",
                "time_window_days",
                "labels",
                "risk_min",
                "max_results",
            ],
        },
        "thread_detail": {
            "name": "Thread Detail",
            "description": "Get full thread details from database",
            "parameters": ["thread_id", "include_body"],
        },
        "security_scan": {
            "name": "Security Scan",
            "description": "Run security analysis on emails",
            "parameters": ["email_ids", "force_rescan"],
        },
        "applications_lookup": {
            "name": "Applications Lookup",
            "description": "Map emails to job applications",
            "parameters": ["email_ids"],
        },
        "profile_stats": {
            "name": "Profile Stats",
            "description": "Get inbox analytics and statistics",
            "parameters": ["time_window_days", "group_by"],
        },
    }

    return {
        "total_tools": len(tools_info),
        "tools": tools_info,
    }


@router.get("/health")
async def agent_health() -> Dict[str, Any]:
    """
    Health check for agent subsystem.

    Checks:
    - Orchestrator initialized
    - Redis connectivity (Phase 2)
    - ES connectivity (Phase 1)
    """
    from app.agent.redis_cache import redis_health_check

    health = {
        "status": "ok",
        "orchestrator": "initialized",
        "components": {},
    }

    # Check Redis (Phase 2)
    try:
        redis_health = await redis_health_check()
        health["components"]["redis"] = redis_health
    except Exception as e:
        health["components"]["redis"] = {"status": "error", "error": str(e)}

    # TODO Phase 1: Check ES connectivity
    # TODO Phase 3: Check LLM provider

    return health
