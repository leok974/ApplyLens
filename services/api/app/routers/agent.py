"""
Agent v2 - API Router

Endpoints:
- POST /agent/mailbox/run - Execute agent run
- GET /agent/mailbox/run/{run_id} - Get run status
- GET /agent/tools - List available tools
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Dict, Any, Optional
import logging
import time
import uuid
from sqlalchemy.orm import Session as DBSession

from app.schemas_agent import (
    AgentRunRequest,
    AgentRunResponse,
    FollowupDraftRequest,
    FollowupDraftResponse,
    FollowupQueueRequest,
    FollowupQueueResponse,
    FollowupStateUpdate,
    InterviewPrepRequest,
    InterviewPrepResponse,
    OpportunitiesSummary,
    RoleMatchBatchRequest,
    RoleMatchBatchResponse,
)
from app.agent.orchestrator import MailboxAgentOrchestrator
from app.db import get_db
from app.models import Session as SessionModel, JobOpportunity, OpportunityMatch
from sqlalchemy import func
from app.metrics import (
    AGENT_TODAY_DURATION_SECONDS,
    FOLLOWUP_DRAFT_REQUESTS,
    FOLLOWUP_QUEUE_REQUESTS,
    FOLLOWUP_QUEUE_ITEM_DONE,
    INTERVIEW_PREP_REQUESTS,
    ROLE_MATCH_REQUESTS,
    ROLE_MATCH_BATCH_REQUESTS,
)

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


def _build_opportunities_summary(
    db: DBSession, owner_email: str
) -> Optional[OpportunitiesSummary]:
    """
    Build opportunities summary for Today view.

    Returns None if no opportunities exist for this user.
    Otherwise returns bucket counts based on existing matches.
    """
    # 1) Check if there are any opportunities for this user
    total_opp = (
        db.query(func.count(JobOpportunity.id))
        .filter(JobOpportunity.owner_email == owner_email)
        .scalar()
    )
    if not total_opp:
        return None

    # 2) Get bucket counts from existing matches
    bucket_counts = (
        db.query(
            OpportunityMatch.match_bucket,
            func.count(OpportunityMatch.id),
        )
        .filter(OpportunityMatch.owner_email == owner_email)
        .group_by(OpportunityMatch.match_bucket)
        .all()
    )

    bucket_map: Dict[str, int] = {b: c for b, c in bucket_counts}

    return OpportunitiesSummary(
        total=total_opp,
        perfect=bucket_map.get("perfect", 0),
        strong=bucket_map.get("strong", 0),
        possible=bucket_map.get("possible", 0),
        skip=bucket_map.get("skip", 0),
    )


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

        # 5. Fetch follow-up queue summary for Today panel
        followups_summary = None
        try:
            from app.models import FollowupQueueState

            # Call get_followup_queue to get the meta
            queue_result = await orchestrator.get_followup_queue(
                user_id=user_id,
                time_window_days=time_window_days,
            )

            if queue_result:
                threads = queue_result.get("threads", [])
                total = len(threads)

                # Fetch state to calculate done_count
                state_rows = (
                    db.query(FollowupQueueState)
                    .filter(FollowupQueueState.user_id == user_id)
                    .all()
                )
                state_by_thread = {row.thread_id: row for row in state_rows}

                done_count = sum(
                    1
                    for thread in threads
                    if state_by_thread.get(thread.get("thread_id", ""), None)
                    and state_by_thread[thread["thread_id"]].is_done
                )
                remaining_count = total - done_count

                followups_summary = {
                    "total": total,
                    "done_count": done_count,
                    "remaining_count": remaining_count,
                    "time_window_days": queue_result.get(
                        "time_window_days", time_window_days
                    ),
                }
        except Exception as e:
            logger.warning(
                f"Today: failed to fetch followups summary: {e}",
                exc_info=True,
            )
            # Continue without followups summary (graceful degradation)

        # 6. Fetch opportunities summary for Today panel
        opportunities_summary = None
        try:
            opportunities_summary = _build_opportunities_summary(db, user_id)
        except Exception as e:
            logger.warning(
                f"Today: failed to fetch opportunities summary: {e}",
                exc_info=True,
            )
            # Continue without opportunities summary (graceful degradation)

        response = {
            "status": "ok",
            "intents": results,
        }
        if followups_summary:
            response["followups"] = followups_summary
        if opportunities_summary:
            response["opportunities"] = opportunities_summary.dict()

        return response

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


@router.post("/followup-draft", response_model=FollowupDraftResponse)
async def draft_followup(
    payload: FollowupDraftRequest,
    req: Request,
    db: DBSession = Depends(get_db),
) -> FollowupDraftResponse:
    """
    Generate a draft follow-up email for a recruiter thread.

    Uses existing Agent V2 machinery to:
    1. Fetch thread details from Gmail
    2. Look up application context if available
    3. Generate a professional follow-up email draft

    Example request:
    ```json
    {
      "user_id": "user@example.com",
      "thread_id": "thread-abc123",
      "application_id": 42,
      "mode": "preview_only"
    }
    ```

    Example response:
    ```json
    {
      "status": "ok",
      "draft": {
        "subject": "Re: Software Engineer - Next Steps?",
        "body": "Hi [Name],\\n\\nI wanted to follow up..."
      }
    }
    ```
    """
    try:
        # Record metric
        FOLLOWUP_DRAFT_REQUESTS.labels(source="thread_viewer").inc()

        # 1. Resolve user_id (same pattern as other endpoints)
        user_id = payload.user_id

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
                        logger.info(
                            f"Followup Draft: resolved user_id={user_id} from session"
                        )

        if not user_id:
            logger.warning("Followup Draft: no user_id resolved, returning 401")
            raise HTTPException(status_code=401, detail="Not authenticated")

        # 2. Validate thread_id
        if not payload.thread_id:
            raise HTTPException(status_code=400, detail="thread_id is required")

        # 3. Call orchestrator to generate draft
        orchestrator = get_orchestrator()
        response = await orchestrator.draft_followup(payload, db=db)

        logger.info(
            f"Followup Draft: completed for user={user_id}, thread={payload.thread_id}, status={response.status}"
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Followup Draft endpoint failed",
            extra={
                "payload": payload.dict() if hasattr(payload, "dict") else str(payload)
            },
        )
        return FollowupDraftResponse(
            status="error", message=f"Failed to generate follow-up draft: {str(e)}"
        )


@router.api_route(
    "/followup-queue",
    methods=["GET", "POST"],
    response_model=FollowupQueueResponse,
)
async def get_followup_queue(
    req: Request,
    db: DBSession = Depends(get_db),
    payload: FollowupQueueRequest | None = None,
):
    """
    Get merged follow-up queue from mailbox threads and tracker applications.

    Returns a prioritized list of items that need follow-up action.
    Supports both GET (for simple queries) and POST (for custom parameters).
    """
    from app.schemas_agent import (
        FollowupQueueResponse,
        QueueMeta,
        QueueItem,
    )
    from app.models import Application

    FOLLOWUP_QUEUE_REQUESTS.inc()

    try:
        # Resolve user_id from session or payload
        user_id = payload.user_id if payload else None
        time_window_days = payload.time_window_days if payload else 30

        if not user_id:
            session_user_id = (
                req.state.session_user_id
                if hasattr(req.state, "session_user_id")
                else None
            )
            if not session_user_id:
                return FollowupQueueResponse(
                    status="error", message="user_id required or valid session"
                )
            user_id = session_user_id

        # Get mailbox followups from agent
        orchestrator = get_orchestrator()
        agent_result = await orchestrator.get_followup_queue(
            user_id=user_id,
            time_window_days=time_window_days,
        )

        threads = agent_result.get("threads", [])

        # Query applications that need followup
        # Criteria: has thread_id AND status in (applied, hr_screen, interview)
        # Note: We don't filter by user here because threads are already user-filtered
        # and we match applications by thread_id
        needs_followup_statuses = ["applied", "hr_screen", "interview"]
        apps = (
            db.query(Application)
            .filter(
                Application.thread_id.isnot(None),
                Application.status.in_(needs_followup_statuses),
            )
            .all()
        )

        # Build lookup by thread_id
        apps_by_thread = {app.thread_id: app for app in apps if app.thread_id}

        # Merge threads and applications
        queue_items = []
        seen_threads = set()

        for thread in threads:
            thread_id = thread["thread_id"]
            if not thread_id:
                continue

            seen_threads.add(thread_id)
            app = apps_by_thread.get(thread_id)

            # Determine priority: threads with applications get higher priority
            priority = thread.get("priority", 50)
            if app:
                priority = max(priority, 70)  # Boost priority if has application

            # Build reason tags
            reason_tags = ["pending_reply"]
            if app:
                reason_tags.append(f"status:{app.status}")

            queue_items.append(
                QueueItem(
                    thread_id=thread_id,
                    application_id=app.id if app else None,
                    priority=priority,
                    reason_tags=reason_tags,
                    company=app.company if app else None,
                    role=app.role if app else None,
                    subject=thread.get("subject"),
                    snippet=thread.get("snippet"),
                    last_message_at=thread.get("last_message_at"),
                    status=app.status if app else None,
                    gmail_url=thread.get("gmail_url"),
                    is_done=False,
                )
            )

        # Add applications without matching threads
        for app in apps:
            if app.thread_id and app.thread_id not in seen_threads:
                queue_items.append(
                    QueueItem(
                        thread_id=app.thread_id,
                        application_id=app.id,
                        priority=60,  # Medium priority for app-only items
                        reason_tags=[f"status:{app.status}", "no_thread_data"],
                        company=app.company,
                        role=app.role,
                        subject=None,
                        snippet=None,
                        last_message_at=None,
                        status=app.status,
                        gmail_url=None,
                        is_done=False,
                    )
                )

        # Sort by priority descending
        queue_items.sort(key=lambda x: x.priority, reverse=True)

        # Fetch followup state for this user
        from app.models import FollowupQueueState

        state_rows = (
            db.query(FollowupQueueState)
            .filter(FollowupQueueState.user_id == user_id)
            .all()
        )
        state_by_thread = {row.thread_id: row for row in state_rows}

        # Apply state to queue items
        done_count = 0
        for item in queue_items:
            state = state_by_thread.get(item.thread_id)
            if state:
                item.is_done = state.is_done
                if state.is_done:
                    done_count += 1

        remaining_count = len(queue_items) - done_count

        return FollowupQueueResponse(
            status="ok",
            queue_meta=QueueMeta(
                total=len(queue_items),
                time_window_days=time_window_days,
                done_count=done_count,
                remaining_count=remaining_count,
            ),
            items=queue_items,
        )

    except Exception as e:
        logger.exception("Error generating followup queue")
        return FollowupQueueResponse(
            status="error", message=f"Failed to generate followup queue: {str(e)}"
        )


@router.post("/followups/state")
async def update_followup_state(
    payload: FollowupStateUpdate,
    req: Request,
    db: DBSession = Depends(get_db),
):
    """
    Update the done state of a follow-up item.

    Upserts into followup_queue_state table.
    """
    from app.models import FollowupQueueState
    from datetime import datetime, timezone

    try:
        # Resolve user_id from session
        user_id = (
            req.state.session_user_id if hasattr(req.state, "session_user_id") else None
        )
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Find existing state row
        state = (
            db.query(FollowupQueueState)
            .filter(
                FollowupQueueState.user_id == user_id,
                FollowupQueueState.thread_id == payload.thread_id,
            )
            .first()
        )

        if state:
            # Update existing
            old_is_done = state.is_done
            state.is_done = payload.is_done
            state.application_id = payload.application_id

            # Set done_at when transitioning to done
            if payload.is_done and not old_is_done:
                state.done_at = datetime.now(timezone.utc)
                FOLLOWUP_QUEUE_ITEM_DONE.inc()
            elif not payload.is_done and old_is_done:
                # Reset done_at when unmarking
                state.done_at = None
        else:
            # Create new
            state = FollowupQueueState(
                user_id=user_id,
                thread_id=payload.thread_id,
                application_id=payload.application_id,
                is_done=payload.is_done,
                done_at=datetime.now(timezone.utc) if payload.is_done else None,
            )
            db.add(state)

            if payload.is_done:
                FOLLOWUP_QUEUE_ITEM_DONE.inc()

        db.commit()

        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating followup state")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interview-prep", response_model=InterviewPrepResponse)
async def get_interview_prep(
    payload: InterviewPrepRequest,
    req: Request,
    db: DBSession = Depends(get_db),
) -> InterviewPrepResponse:
    """
    Generate interview preparation materials for an application.

    Loads application metadata and related email threads, then uses LLM to generate
    structured interview prep content including:
    - Company and role overview
    - Timeline of application progress
    - Interview details (date, format, status)
    - Preparation sections (what to review, questions to ask)

    Example request:
    ```json
    {
      "application_id": 42,
      "thread_id": "thread-abc123",
      "preview_only": true
    }
    ```

    Example response:
    ```json
    {
      "company": "Acme Corp",
      "role": "Senior Software Engineer",
      "interview_status": "Scheduled",
      "interview_date": "2025-12-01T14:00:00Z",
      "interview_format": "Zoom",
      "timeline": ["Applied on Nov 15", "HR screen on Nov 20", "Interview scheduled for Dec 1"],
      "sections": [
        {
          "title": "What to Review",
          "bullets": ["Review job description", "Research company products", "Prepare examples"]
        },
        {
          "title": "Questions to Ask",
          "bullets": ["Ask about team structure", "Inquire about tech stack", "Learn about growth opportunities"]
        }
      ]
    }
    ```
    """
    try:
        # Record metric
        source = "tracker" if not payload.thread_id else "thread_viewer"
        INTERVIEW_PREP_REQUESTS.labels(source=source).inc()

        # Resolve user_id from session
        user_id = None
        sid = req.cookies.get("session_id")
        if sid:
            sess = db.query(SessionModel).filter(SessionModel.id == sid).first()
            if sess and sess.user_id:
                from app.models import User as UserModel

                user = db.query(UserModel).filter(UserModel.id == sess.user_id).first()
                if user and user.email:
                    user_id = user.email
                    logger.info(
                        f"Interview Prep: resolved user_id={user_id} from session"
                    )

        if not user_id:
            logger.warning("Interview Prep: no user_id resolved, returning 401")
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Create request context for orchestrator
        from app.config import RequestContext

        ctx = RequestContext(user_id=user_id, db_session=db)

        # Call orchestrator
        orchestrator = MailboxAgentOrchestrator(ctx=ctx)
        response = await orchestrator.interview_prep(payload)

        logger.info(
            f"Interview Prep: completed for application_id={payload.application_id}, thread_id={payload.thread_id}"
        )
        return response

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Interview Prep validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            "Interview Prep endpoint failed",
            extra={
                "payload": payload.dict() if hasattr(payload, "dict") else str(payload)
            },
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to generate interview prep: {str(e)}"
        )


@router.post("/role-match")
async def match_role(
    opportunity_id: int,
    resume_profile_id: int = None,
    req: Request = None,
    db: DBSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Match a job opportunity against a resume using LLM analysis.

    Analyzes how well the candidate's resume matches the job opportunity and returns:
    - Match bucket (perfect/strong/possible/skip)
    - Match score (0-100)
    - Reasons why it's a good match
    - Missing skills from the job description
    - Resume tweaks to improve the match

    Example request:
    ```
    POST /v2/agent/role-match?opportunity_id=42&resume_profile_id=7
    ```

    Or use active resume if resume_profile_id not provided:
    ```
    POST /v2/agent/role-match?opportunity_id=42
    ```

    Example response:
    ```json
    {
      "match_bucket": "strong",
      "match_score": 82,
      "reasons": [
        "5+ years Python experience matches requirement",
        "React expertise aligns with frontend needs",
        "Previous fintech experience relevant"
      ],
      "missing_skills": ["Kubernetes", "GraphQL"],
      "resume_tweaks": [
        "Highlight AWS certifications in summary",
        "Add specific Docker project examples"
      ],
      "opportunity": {
        "id": 42,
        "title": "Senior Full Stack Engineer",
        "company": "Acme Corp"
      },
      "resume": {
        "id": 7,
        "headline": "Senior Software Engineer"
      }
    }
    ```
    """
    try:
        # Resolve user_id from session
        user_id = None
        sid = req.cookies.get("session_id")
        if sid:
            sess = db.query(SessionModel).filter(SessionModel.id == sid).first()
            if sess and sess.user_id:
                from app.models import User as UserModel

                user = db.query(UserModel).filter(UserModel.id == sess.user_id).first()
                if user and user.email:
                    user_id = user.email
                    logger.info(f"Role Match: resolved user_id={user_id} from session")

        if not user_id:
            logger.warning("Role Match: no user_id resolved, returning 401")
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Create request context for orchestrator
        from app.config import RequestContext

        ctx = RequestContext(user_id=user_id, db_session=db)

        # Call orchestrator
        orchestrator = MailboxAgentOrchestrator(ctx=ctx)
        response = await orchestrator.role_match(
            opportunity_id=opportunity_id,
            resume_profile_id=resume_profile_id,
        )

        # Record metric
        match_bucket = response.get("match_bucket", "unknown")
        ROLE_MATCH_REQUESTS.labels(match_bucket=match_bucket).inc()

        logger.info(
            f"Role Match: completed for opportunity_id={opportunity_id}, bucket={match_bucket}, score={response.get('match_score')}"
        )
        return response

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Role Match validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            "Role Match endpoint failed",
            extra={
                "opportunity_id": opportunity_id,
                "resume_profile_id": resume_profile_id,
            },
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to generate role match: {str(e)}"
        )


@router.post("/role-match/batch", response_model=RoleMatchBatchResponse)
async def agent_role_match_batch(
    payload: RoleMatchBatchRequest,
    req: Request = None,
    db: DBSession = Depends(get_db),
) -> RoleMatchBatchResponse:
    """
    Batch match all unmatched opportunities for the authenticated user.

    Finds all opportunities that don't have a match record and runs
    role matching on each using the active resume profile.

    Example request:
    ```json
    {
      "limit": 50
    }
    ```

    Example response:
    ```json
    {
      "processed": 12,
      "items": [
        {
          "opportunity_id": 42,
          "match_bucket": "strong",
          "match_score": 82
        },
        ...
      ]
    }
    ```
    """
    try:
        # Resolve user_id from session
        user_id = None
        sid = req.cookies.get("session_id")
        if sid:
            sess = db.query(SessionModel).filter(SessionModel.id == sid).first()
            if sess and sess.user_id:
                from app.models import User as UserModel

                user = db.query(UserModel).filter(UserModel.id == sess.user_id).first()
                if user and user.email:
                    user_id = user.email
                    logger.info(
                        f"Batch Role Match: resolved user_id={user_id} from session"
                    )

        if not user_id:
            logger.warning("Batch Role Match: no user_id resolved, returning 401")
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Create request context for orchestrator
        from app.config import RequestContext

        ctx = RequestContext(user_id=user_id, db_session=db)

        # Call orchestrator
        orchestrator = MailboxAgentOrchestrator(ctx=ctx)
        response = await orchestrator.role_match_batch(payload)

        # Record metric
        ROLE_MATCH_BATCH_REQUESTS.inc()

        logger.info(
            f"Batch Role Match: completed, processed {response.processed} opportunities for user {user_id}"
        )
        return response

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Batch Role Match validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            "Batch Role Match endpoint failed",
            extra={"user_id": user_id if "user_id" in locals() else None},
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to batch match opportunities: {str(e)}"
        )
