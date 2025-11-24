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
import time
import uuid
from sqlalchemy.orm import Session as DBSession

from app.schemas_agent import AgentRunRequest, AgentRunResponse
from app.agent.orchestrator import MailboxAgentOrchestrator
from app.db import get_db
from app.models import Session as SessionModel
from app.metrics import AGENT_TODAY_DURATION_SECONDS

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
        response = await orchestrator.run(payload, db=db)

        logger.info(
            f"Agent V2: run completed: run_id={response.run_id}, status={response.status}"
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Agent V2 run failed",
            extra={
                "query": payload.query,
                "user_id": user_id if "user_id" in locals() else None,
            },
        )
        # Return 200 with error payload instead of 500 to avoid Cloudflare 502
        return AgentRunResponse(
            run_id=f"error-{uuid.uuid4()}",
            user_id=user_id if "user_id" in locals() else "unknown",
            query=payload.query,
            mode=payload.mode,
            context=payload.context,
            status="error",
            error_message=f"Internal error while running Mailbox Assistant: {str(e)}",
            cards=[],
            intent="unknown",
            answer="I hit an error while running the Mailbox Assistant. Please try again.",
        )


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


@router.post("/today")
async def today_triage(
    payload: Dict[str, Any],
    req: Request,
    db: DBSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Execute "Today" inbox triage across multiple scan intents.

    Runs preview_only scans for a fixed set of intents:
    - followups
    - bills
    - interviews
    - unsubscribe
    - clean_promos
    - suspicious

    Returns compact summary + limited threads for each intent.

    Example request:
    ```json
    {
      "user_id": "user@example.com",  // optional if session cookie present
      "time_window_days": 90
    }
    ```

    Example response:
    ```json
    {
      "status": "ok",
      "intents": [
        {
          "intent": "followups",
          "summary": {"count": 2, "time_window_days": 90},
          "threads": [...]
        },
        ...
      ]
    }
    ```
    """
    start = time.perf_counter()
    try:
        # 1. Resolve user_id (same pattern as /run endpoint)
        user_id = payload.get("user_id")

        if not user_id:
            sid = req.cookies.get("session_id")
            if sid:
                sess = db.query(SessionModel).filter(SessionModel.id == sid).first()
                if sess and sess.user_id:
                    from app.models import User as UserModel

                    user = (
                        db.query(UserModel).filter(UserModel.id == sess.user_id).first()
                    )
                    if user and user.email:
                        user_id = user.email
                        logger.info(f"Today: resolved user_id={user_id} from session")

        if not user_id:
            logger.warning("Today: no user_id resolved, returning 401")
            raise HTTPException(status_code=401, detail="Not authenticated")

        # 2. Extract time_window_days (default to 90)
        time_window_days = payload.get("time_window_days", 90)

        # 3. Fixed list of scan intents for Today view
        scan_intents = [
            "followups",
            "bills",
            "interviews",
            "unsubscribe",
            "clean_promos",
            "suspicious",
        ]

        # 4. Run preview_only scan for each intent
        orchestrator = get_orchestrator()
        results = []

        for intent in scan_intents:
            try:
                # Build request for this intent
                request = AgentRunRequest(
                    user_id=user_id,
                    query=f"Show {intent}",  # Simple query to trigger intent
                    mode="preview_only",
                    intent=intent,  # Explicit intent override
                    context={"time_window_days": time_window_days},
                )

                # Execute scan
                response = await orchestrator.run(request, db=db)

                # Extract summary + threads from cards
                summary = {"count": 0, "time_window_days": time_window_days}
                threads = []

                for card in response.cards:
                    # Extract count from meta
                    if card.meta and "count" in card.meta:
                        summary["count"] = card.meta["count"]
                        summary["time_window_days"] = card.meta.get(
                            "time_window_days", time_window_days
                        )

                    # Extract threads from thread_list cards
                    if card.kind == "thread_list" and hasattr(card, "threads"):
                        threads = card.threads[:5]  # Limit to 5 threads per intent

                results.append(
                    {
                        "intent": intent,
                        "summary": summary,
                        "threads": threads,
                    }
                )

            except Exception as e:
                # Log error but continue with other intents
                logger.error(
                    f"Today: intent '{intent}' failed: {e}",
                    exc_info=True,
                    extra={"user_id": user_id, "intent": intent},
                )
                # Omit failed intent from results (graceful degradation)
                continue

        logger.info(
            f"Today: completed for user={user_id}, {len(results)}/{len(scan_intents)} intents succeeded"
        )

        return {
            "status": "ok",
            "intents": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Today endpoint failed", extra={"payload": payload})
        raise HTTPException(
            status_code=500,
            detail=f"Today triage failed: {str(e)}",
        )
    finally:
        duration = time.perf_counter() - start
        # Guard against negative duration (shouldn't happen with perf_counter)
        if duration >= 0:
            AGENT_TODAY_DURATION_SECONDS.observe(duration)


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
