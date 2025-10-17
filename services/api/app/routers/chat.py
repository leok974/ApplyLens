"""
Chat router for conversational mailbox assistant.

Provides POST /chat endpoint that:
1. Detects user intent from message
2. Performs RAG search over emails
3. Routes to appropriate tool function
4. Returns structured response with answer, actions, and citations
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.intent import (
    detect_intent,
    explain_intent,
    explain_intent_tokens,
    extract_unless_brands,
)
from ..core.mail_tools import (
    clean_promos,
    create_calendar_events,
    create_tasks,
    find_emails,
    flag_suspicious,
    follow_up,
    summarize_emails,
    unsubscribe_inactive,
)
from ..core.rag import rag_search
from ..db import SessionLocal
from ..deps.user import get_current_user_email
from ..deps.params import clamp_window_days
from ..metrics import record_tool
from ..models import ActionType, AuditAction, Policy, ProposedAction
from ..settings import settings

logger = logging.getLogger(__name__)

# Elasticsearch configuration
# Use ES_URL (set in docker-compose) or fall back to ELASTICSEARCH_URL
ES_URL = os.getenv("ES_URL") or os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
ES_ENABLED = True
try:
    from elasticsearch import Elasticsearch

    # Test connection
    _es_test = Elasticsearch(ES_URL)
    _es_test.ping()
except Exception as e:
    ES_ENABLED = False
    logger.warning(f"Elasticsearch not available for chat: {e}")


def get_es():
    """Get Elasticsearch client."""
    if not ES_ENABLED:
        raise HTTPException(
            status_code=503, detail="Elasticsearch service not available"
        )
    try:
        return Elasticsearch(ES_URL)
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Failed to connect to Elasticsearch: {e}"
        )


router = APIRouter(prefix="/chat", tags=["chat"])


class Message(BaseModel):
    """A single message in the conversation."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Request for chat endpoint."""

    messages: List[Message] = Field(
        ..., description="Conversation history with last message being user query"
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured filters: category, risk_min, sender_domain, date_from, date_to, labels",
    )
    max_results: int = Field(
        default=50, ge=1, le=100, description="Maximum number of emails to search"
    )
    window_days: Optional[int] = Field(
        default=30, ge=1, le=365, description="Time window in days to search (default: 30)"
    )


class Citation(BaseModel):
    """Email citation with key metadata."""

    id: str
    subject: str
    sender: Optional[str] = None
    received_at: Optional[str] = None
    category: Optional[str] = None
    risk_score: Optional[int] = None


class ActionItem(BaseModel):
    """Proposed action on an email."""

    action: str = Field(
        ..., description="Action type (archive_email, unsubscribe_via_header, etc.)"
    )
    email_id: str = Field(..., description="Email ID to perform action on")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Action-specific parameters"
    )


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    intent: str = Field(..., description="Detected user intent")
    intent_explanation: str = Field(..., description="What the intent does")
    answer: str = Field(..., description="Natural language response")
    actions: List[ActionItem] = Field(
        default_factory=list, description="Proposed actions"
    )
    citations: List[Citation] = Field(
        default_factory=list, description="Email sources used"
    )
    search_stats: Dict[str, Any] = Field(
        default_factory=dict,
        description="Search metadata (total results, query, filters)",
    )
    timing: Dict[str, Any] = Field(
        default_factory=dict,
        description="Performance timing (es_ms, llm_ms)",
    )


# System prompt for future LLM integration
SYSTEM_PROMPT = """You are ApplyLens Mailbox Assistant.
Tools you can call:
- summarize(query, filters) → brief bullet summary of matching emails
- find(query, filters) → list matching emails with reasons
- clean(filters) → propose archiving per policy
- unsubscribe(filters) → propose unsubscribe via List-Unsubscribe
- flag(filters) → surface suspicious with explanations
- follow_up(filters) → draft follow-ups for threads needing reply
- calendar(filters) → create event reminders
- task(filters) → create tasks

Behavior:
- Always cite the emails you used (subject, date, sender, id).
- Never hallucinate IDs; only use those returned by search.
- Respect policies (risk/quarantine/promo rules).
- Prefer concise bullets.
"""


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    es=Depends(get_es),
    user_email: str = Depends(get_current_user_email),
):
    """
    Chat with your mailbox.

    Process natural language queries about emails and return:
    - Detected intent (what you're trying to do)
    - Natural language answer
    - Proposed actions (if applicable)
    - Citations (source emails)

    Example queries:
    - "Summarize recent emails about job applications"
    - "What bills are due before Friday? Create calendar reminders."
    - "Clean up promos older than a week unless they're from Best Buy"
    - "Show suspicious emails from new domains this week"
    - "Unsubscribe from newsletters I haven't opened in 60 days"
    """
    # Extract user's latest message
    if not req.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    user_text = req.messages[-1].content
    if not user_text.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    # Detect intent
    intent = detect_intent(user_text)
    intent_explanation = explain_intent(intent)

    # Perform RAG search for email context
    # CRITICAL: Always filter by owner_email for multi-user support
    # Default to "*" query if empty to avoid empty queries
    search_query = user_text.strip() or "*"

    # Calculate time window filter
    window_days = clamp_window_days(req.window_days, default=30, mn=1, mx=365)
    from datetime import timedelta
    since = (datetime.utcnow() - timedelta(days=window_days)).isoformat()
    
    # Add date range filter to existing filters
    merged_filters = {**req.filters}
    if "received_at" not in merged_filters:
        merged_filters["received_at"] = {"gte": since}

    try:
        rag = rag_search(
            es,
            search_query,
            filters=merged_filters,
            k=req.max_results,
            owner_email=user_email,  # NEW: Pass owner_email for scoping
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    # Route to appropriate tool based on intent
    try:
        if intent == "summarize":
            answer, actions = summarize_emails(rag, user_text)
        elif intent == "find":
            answer, actions = find_emails(rag, user_text, owner_email=user_email)
        elif intent == "clean":
            answer, actions = clean_promos(rag, user_text)
        elif intent == "unsubscribe":
            answer, actions = unsubscribe_inactive(rag, user_text)
        elif intent == "flag":
            answer, actions = flag_suspicious(rag, user_text)
        elif intent == "follow-up":
            answer, actions = follow_up(rag, user_text)
        elif intent == "calendar":
            answer, actions = create_calendar_events(rag, user_text)
        elif intent == "task":
            answer, actions = create_tasks(rag, user_text)
        else:
            # Fallback to summarize
            answer, actions = summarize_emails(rag, user_text)
        
        # Record tool usage metrics
        record_tool(intent, rag.get("total", 0), window_days=window_days)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")

    # Build citations from top email sources
    citations = [
        Citation(
            id=str(d.get("id", "")),
            subject=d.get("subject", "(no subject)"),
            sender=d.get("sender"),
            received_at=d.get("received_at"),
            category=d.get("category"),
            risk_score=d.get("risk_score"),
        )
        for d in rag["docs"][:10]
    ]

    # Build action items
    action_items = [
        ActionItem(
            action=a["action"], email_id=str(a["email_id"]), params=a.get("params", {})
        )
        for a in actions
    ]

    # Search stats for debugging/transparency
    search_stats = {
        "total_results": rag.get("total", 0),
        "returned_results": rag.get("count", 0),
        "query": rag.get("query", ""),
        "filters": rag.get("filters", {}),
        "took_ms": rag.get("took_ms"),  # ES timing
    }
    
    # Timing information for frontend
    timing = {
        "es_ms": rag.get("took_ms"),
        # llm_ms can be added here if you measure LLM call time
    }

    return ChatResponse(
        intent=intent,
        intent_explanation=intent_explanation,
        answer=answer,
        actions=action_items,
        citations=citations,
        search_stats=search_stats,
        timing=timing,
    )


@router.get("/intents")
async def list_intents():
    """
    List all available intents and their descriptions.

    Useful for UI to show quick-action buttons.
    """
    from ..core.intent import INTENTS, explain_intent

    return {
        intent: {
            "patterns": patterns,
            "description": explain_intent(intent),  # type: ignore
        }
        for intent, patterns in INTENTS.items()
    }


@router.get("/health")
async def health():
    """Health check for chat service."""
    return {"status": "ok", "service": "chat"}


@router.get("/stream")
async def chat_stream(
    q: str,
    propose: int = 0,
    remember: int = 0,
    window_days: int = Query(30, ge=1, le=365, description="Time window in days"),
    mode: str = Query(None, description="Special mode: networking|money"),
    es=Depends(get_es),
    user_email: str = Depends(get_current_user_email),
):
    """
    Stream chat responses with Server-Sent Events (SSE).
    
    **Canary Toggle**: Can be disabled via CHAT_STREAMING_ENABLED=false for rollback/testing.

    Query params:
    - q: The user query text
    - propose: If 1, file actions to Approvals tray
    - remember: If 1, learn exceptions from the query (e.g., "unless Best Buy")
    - window_days: Time window in days to search (default: 30, max: 365)
    - mode: Optional mode (networking|money) for specialized boosts

    Events emitted:
    - intent: {"intent": "clean", "explanation": "..."}
    - intent_explain: {"tokens": ["clean", "before friday", "unless best buy"]}
    - tool: {"tool": "clean", "matches": 42, "actions": 5}
    - answer: {"answer": "Here's what I found..."}
    - memory: {"kept_brands": ["best buy"]} - Only if remember=1
    - filed: {"proposed": 5} - Only if propose=1
    - done: {"ok": true}
    - error: {"error": "message"}
    """
    # Canary toggle: allow disabling streaming for rollback/testing
    if not settings.CHAT_STREAMING_ENABLED:
        logger.warning("Streaming disabled by CHAT_STREAMING_ENABLED flag")
        raise HTTPException(
            status_code=503,
            detail="Streaming temporarily disabled. Use /chat endpoint instead.",
            headers={"X-Chat-Streaming-Disabled": "1"}
        )
    
    import asyncio
    import json
    import time

    from fastapi.responses import StreamingResponse

    HEARTBEAT_SEC = 20  # Send keep-alive every 20 seconds

    async def generate():
        last_heartbeat = time.monotonic()
        
        try:
            # Send ready signal
            yield f'event: ready\ndata: {json.dumps({"ok": True})}\n\n'
            await asyncio.sleep(0.01)
            
            # Detect intent
            intent = detect_intent(q)
            intent_explanation = explain_intent(intent)
            matches = explain_intent_tokens(q)
            brands = extract_unless_brands(q)

            yield f'event: intent\ndata: {json.dumps({"intent": intent, "explanation": intent_explanation})}\n\n'
            await asyncio.sleep(0.1)  # Small delay for UI smoothness
            
            # Heartbeat check
            if time.monotonic() - last_heartbeat > HEARTBEAT_SEC:
                yield ": keep-alive\n\n"
                last_heartbeat = time.monotonic()

            # Emit intent explanation tokens
            yield f'event: intent_explain\ndata: {json.dumps({"tokens": matches})}\n\n'
            await asyncio.sleep(0.1)
            
            # Heartbeat check
            if time.monotonic() - last_heartbeat > HEARTBEAT_SEC:
                yield ": keep-alive\n\n"
                last_heartbeat = time.monotonic()

            # Calculate time window filter
            from datetime import timedelta
            window_days_capped = clamp_window_days(window_days, default=30, mn=1, mx=365)
            since = (datetime.utcnow() - timedelta(days=window_days_capped)).isoformat()

            # Perform RAG search with user scoping and time window
            # CRITICAL: Default to "*" if query is empty, always filter by owner_email
            search_query = q.strip() or "*"
            rag = rag_search(
                es=es,
                query=search_query,
                filters={"received_at": {"gte": since}},
                k=50,
                mode=mode,  # Phase 6: Pass mode for specialized boosts
                owner_email=user_email,  # NEW: Always filter by owner_email
            )

            # Route to appropriate tool
            tool_name = intent
            if intent == "summarize":
                answer, actions = summarize_emails(rag, q)
            elif intent == "find":
                answer, actions = find_emails(rag, q, owner_email=user_email)
            elif intent == "clean":
                answer, actions = clean_promos(rag, q)
            elif intent == "unsubscribe":
                answer, actions = unsubscribe_inactive(rag, q)
            elif intent == "flag":
                answer, actions = flag_suspicious(rag, q)
            elif intent == "follow-up":
                answer, actions = follow_up(rag, q)
            elif intent == "calendar":
                answer, actions = create_calendar_events(rag, q)
            elif intent == "task":
                answer, actions = create_tasks(rag, q)
            else:
                answer, actions = summarize_emails(rag, q)

            # Record tool usage metrics
            record_tool(tool_name, rag.get("total", 0), window_days=window_days_capped)
            
            # Heartbeat check
            if time.monotonic() - last_heartbeat > HEARTBEAT_SEC:
                yield ": keep-alive\n\n"
                last_heartbeat = time.monotonic()

            # Emit tool result
            yield f'event: tool\ndata: {json.dumps({"tool": tool_name, "matches": rag.get("total", 0), "actions": len(actions)})}\n\n'
            await asyncio.sleep(0.1)

            # Emit answer
            yield f'event: answer\ndata: {json.dumps({"answer": answer})}\n\n'
            await asyncio.sleep(0.1)

            # If remember=1, learn exceptions from "unless" phrases
            if remember == 1 and len(brands) > 0:
                try:
                    db: Session = SessionLocal()
                    # For each brand, upsert a high-priority 'keep' policy that prevents auto-archive
                    # We rely on 'regex' over 'sender' to be brand-friendly; category 'promo'
                    for brand in brands[:5]:  # Cap at 5 brands
                        pol = Policy(
                            name=f"Learned: keep promos for {brand}",
                            enabled=True,
                            priority=5,  # runs before archive (50)
                            action=ActionType.label_email,  # harmless action to short-circuit archive policy
                            confidence_threshold=0.0,
                            condition={
                                "all": [
                                    {"eq": ["category", "promo"]},
                                    {"regex": ["sender", brand]},
                                ]
                            },
                        )
                        db.add(pol)
                    db.commit()
                    db.close()

                    # Signal memory learned back to UI
                    yield f'event: memory\ndata: {json.dumps({"kept_brands": brands})}\n\n'
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to learn memory: {e}")

            # Build citations for transcript
            citations = [
                {
                    "id": str(d.get("id", "")),
                    "subject": d.get("subject", "(no subject)"),
                    "sender": d.get("sender"),
                    "received_at": d.get("received_at"),
                }
                for d in rag.get("docs", [])[:10]
            ]

            # If propose=1, file actions to Approvals tray with transcript
            if propose == 1 and len(actions) > 0:
                # Cap at 100 actions for safety
                capped_actions = actions[:100]

                # Lightweight transcript (stored on proposed + audit rows)
                transcript = {
                    "via": "chat",
                    "query": q,
                    "intent": intent,
                    "tool": tool_name,
                    "tokens": matches,
                    "citations": citations,
                    "count_matches": len(rag.get("docs", [])),
                    "count_actions": len(actions),
                }

                # File to ProposedAction and AuditAction (so Approvals tray shows transcript instantly)
                try:
                    db: Session = SessionLocal()
                    created = 0
                    for a in capped_actions:
                        # Create proposed action
                        pa = ProposedAction(
                            email_id=int(a["email_id"]),
                            action=ActionType(a["action"]),
                            params=a.get("params") or {},
                            confidence=0.8,
                            rationale={"via": "chat", "transcript": transcript},
                            policy_id=None,
                        )
                        db.add(pa)
                        created += 1

                        # Also write 'proposed' to audit trail immediately (transcript export)
                        db.add(
                            AuditAction(
                                email_id=int(a["email_id"]),
                                action=ActionType(a["action"]),
                                params=a.get("params") or {},
                                actor=user_email,  # Use user_email from dependency
                                outcome="proposed",
                                error=None,
                                why={"via": "chat", "transcript": transcript},
                                screenshot_path=None,
                            )
                        )

                    db.commit()
                    db.close()

                    # Emit filed confirmation
                    yield f'event: filed\ndata: {json.dumps({"proposed": created})}\n\n'
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to file actions: {e}")
                    yield f'event: error\ndata: {json.dumps({"error": f"Failed to file actions: {str(e)}"})}\n\n'

            # Done
            yield f'event: done\ndata: {json.dumps({"ok": True})}\n\n'

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f'event: error\ndata: {json.dumps({"error": str(e)})}\n\n'

    return StreamingResponse(generate(), media_type="text/event-stream")


# Legacy placeholder (kept for reference)
# Future: Streaming endpoint for real-time token generation
# @router.post("/stream")
# async def chat_stream(req: ChatRequest, es=Depends(get_es)):
#     """Stream chat responses token by token."""
#     async def generate():
#         # Yield tokens as they're generated
#         yield f"data: {json.dumps({'token': '...', 'done': False})}\n\n"
#
#     return StreamingResponse(generate(), media_type="text/event-stream")
