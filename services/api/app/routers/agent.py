"""
Agent v2 - API Router

Endpoints:
- POST /agent/mailbox/run - Execute agent run
- GET /agent/mailbox/run/{run_id} - Get run status
- GET /agent/tools - List available tools
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Dict, Any
import logging
from sqlalchemy.orm import Session as DBSession

from app.schemas_agent import AgentRunRequest, AgentRunResponse
from app.agent.orchestrator import MailboxAgentOrchestrator
from app.db import get_db
from app.models import Session as SessionModel

router = APIRouter(prefix="/v2/agent", tags=["agent-v2"])
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


@router.post("/run", response_model=AgentRunResponse)
async def run_mailbox_agent(
    payload: AgentRunRequest,
    req: Request,
    db: DBSession = Depends(get_db),
):
    """
    Execute a mailbox agent run.

    Flow:
    1. Resolve user from session or explicit user_id
    2. Classify intent from query
    3. Plan + execute tools
    4. Synthesize answer with LLM
    5. Return structured response with cards

    Example request:
    ```json
    {
      "query": "Show suspicious emails from new domains this week",
      "mode": "preview_only",
      "context": {
        "time_window_days": 7,
        "filters": {"labels": ["INBOX"], "risk_min": 80}
      }
    }
    ```
    """
    try:
        # 1. If caller sent user_id explicitly (smoke harness, tests), use it
        user_id = payload.user_id

        # 2. Otherwise, derive from session cookie (same pattern as auth.py)
        if not user_id:
            sid = req.cookies.get("session_id")

            logger.info(
                f"Agent V2: incoming sid={sid!r}, payload.user_id={payload.user_id!r}"
            )

            if sid:
                sess = db.query(SessionModel).filter(SessionModel.id == sid).first()
                if sess and sess.user_id:
                    from app.models import User as UserModel

                    user = (
                        db.query(UserModel).filter(UserModel.id == sess.user_id).first()
                    )
                    if user and user.email:
                        user_id = user.email
                        logger.info(
                            f"Agent V2: resolved user_id={user_id!r} from session"
                        )
                    else:
                        logger.warning(
                            "Agent V2: session has user_id but no matching user/email"
                        )
                else:
                    logger.warning("Agent V2: no session row for sid from cookie")
            else:
                logger.warning("Agent V2: no session cookie on request")

        # 3. If we STILL don't have a user_id, fail clearly
        if not user_id:
            logger.warning("Agent V2: no user_id resolved, returning 401")
            raise HTTPException(status_code=401, detail="Not authenticated")

        # 4. Mutate the payload and hand off to the orchestrator
        payload.user_id = user_id
        logger.info(
            f"Agent V2: executing run for user={user_id}, query='{payload.query}'"
        )

        orchestrator = get_orchestrator()
        response = await orchestrator.run(payload)

        logger.info(
            f"Agent V2: run completed: run_id={response.run_id}, status={response.status}"
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent V2: run failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent run failed: {str(e)}")


@router.get("/run/{run_id}", response_model=AgentRunResponse)
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
