from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal, List, Optional, Dict, Any
import datetime as dt
import os
import httpx

from elasticsearch import Elasticsearch
from app.llm_provider import generate_llm_text, generate_assistant_text

router = APIRouter(prefix="/assistant", tags=["assistant"])

# Elasticsearch setup
ES_INDEX = os.getenv("ELASTICSEARCH_INDEX", "gmail_emails")
ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200")
ES_ENABLED = os.getenv("ES_ENABLED", "true").lower() == "true"


def get_es_client() -> Elasticsearch:
    """Get Elasticsearch client for assistant queries."""
    if not ES_ENABLED:
        return None
    return Elasticsearch(ES_URL)


class ContextHint(BaseModel):
    """Short-term memory hint from previous interaction."""

    previous_intent: Optional[str] = None
    previous_email_ids: List[str] = []


class AssistantQueryRequest(BaseModel):
    user_query: str
    time_window_days: int = 30  # 7 | 30 | 60 etc.
    mode: Literal["off", "run"] = "off"
    memory_opt_in: bool = False
    account: str  # gmail account / user identity context
    context_hint: Optional[ContextHint] = None  # Phase 3: short-term memory


class AssistantEmailSource(BaseModel):
    id: str
    sender: str
    subject: str
    timestamp: str
    risk_score: Optional[float] = None
    quarantined: Optional[bool] = None
    amount: Optional[float] = None
    due_date: Optional[str] = None
    unsubscribe_candidate: Optional[bool] = None
    reply_needed: Optional[bool] = None


class AssistantSuggestedAction(BaseModel):
    label: str
    kind: Literal[
        "external_link",
        "unsubscribe",
        "mark_safe",
        "archive",
        "follow_up",
        "draft_reply",
    ]
    email_id: Optional[str] = None
    link: Optional[str] = None
    sender: Optional[str] = None
    subject: Optional[str] = None


class AssistantActionPerformed(BaseModel):
    type: str
    status: str
    target: Optional[str] = None


class AssistantQueryResponse(BaseModel):
    intent: str
    summary: str
    sources: List[AssistantEmailSource]
    suggested_actions: List[AssistantSuggestedAction]
    actions_performed: List[AssistantActionPerformed] = []
    next_steps: Optional[str] = None  # conversational CTA
    followup_prompt: Optional[str] = None  # "You can also ask me ..."
    llm_used: Optional[str] = (
        None  # "ollama", "openai", "fallback" - telemetry for LLM usage
    )


@router.post("/query", response_model=AssistantQueryResponse)
async def assistant_query(payload: AssistantQueryRequest):
    """
    Core entry point for Mailbox Assistant.

    1. Classify intent from payload.user_query (or chip text) - now with LLM fallback
    2. Run intent-specific query planners
    3. (optional) run mutations if mode=="run"
    4. Generate polished summary with LLM (if available)
    5. Return structured answer
    """

    # 1. Classify intent (keyword matching + LLM fallback)
    intent = await classify_intent(payload.user_query)

    # 2. Plan + fetch
    fetched = await run_intent_plan(
        intent=intent,
        days=payload.time_window_days,
        account=payload.account,
    )
    # fetched = {"summary": str, "emails": [...], "suggested_actions": [...]}
    # emails are raw dicts with keys matching AssistantEmailSource

    actions_performed: List[AssistantActionPerformed] = []

    # 3. Optionally apply actions if mode=="run"
    if payload.mode == "run":
        actions_performed = await maybe_apply_bulk_actions(
            intent=intent,
            fetched=fetched,
            account=payload.account,
            memory_opt_in=payload.memory_opt_in,
        )

    # 4. Generate polished summary with LLM (graceful fallback to base summary)
    base_summary = fetched["summary"]
    final_summary, llm_used = await generate_polished_summary(
        intent=intent,
        base_summary=base_summary,
        emails=fetched["emails"],
        actions_performed=actions_performed,
        mode=payload.mode,
        days=payload.time_window_days,
    )

    # 5. Build response
    return AssistantQueryResponse(
        intent=intent,
        summary=final_summary,
        sources=[AssistantEmailSource(**e) for e in fetched["emails"]],
        suggested_actions=[
            AssistantSuggestedAction(**a) for a in fetched["suggested_actions"]
        ],
        actions_performed=actions_performed,
        llm_used=llm_used,  # Phase 3: telemetry for LLM usage
    )


# -------- Draft Reply Endpoint --------


class DraftReplyRequest(BaseModel):
    email_id: str
    sender: str
    subject: str
    account: str
    thread_summary: Optional[str] = None  # Optional context about the conversation
    tone: Optional[str] = None  # Optional: "warmer", "more_direct", "formal", "casual"


class DraftReplyResponse(BaseModel):
    email_id: str
    draft: str
    sender: str
    subject: str


@router.post("/draft-reply", response_model=DraftReplyResponse)
async def draft_reply(payload: DraftReplyRequest):
    """
    Generate a polite follow-up reply draft for a specific email.

    This is the "close the loop" feature that bridges:
    Inbox → Tracker → Reply

    Perfect for job seekers to stay in the "I'm actively interviewing" loop.
    """

    # Build context for LLM
    context_parts = [
        f"Sender: {payload.sender}",
        f"Subject: {payload.subject}",
    ]

    if payload.thread_summary:
        context_parts.append(f"Context: {payload.thread_summary}")

    context = "\n".join(context_parts)

    # Determine tone instructions
    tone_instruction = ""
    if payload.tone == "warmer":
        tone_instruction = "- Use a warmer, more enthusiastic tone\n"
    elif payload.tone == "more_direct":
        tone_instruction = "- Be more direct and to the point\n"
    elif payload.tone == "formal":
        tone_instruction = "- Use a more formal, professional tone\n"
    elif payload.tone == "casual":
        tone_instruction = "- Use a more casual, relaxed tone\n"

    # Build LLM prompt for drafting reply
    prompt = (
        "You are helping a job seeker draft a polite follow-up email.\n\n"
        f"{context}\n\n"
        "Draft a short, professional follow-up that:\n"
        "- Confirms continued interest\n"
        "- Asks politely about next steps\n"
        "- Stays concise (2-3 sentences)\n"
        f"{tone_instruction}"
        "- Uses a friendly but professional tone\n"
        "- Does NOT include subject line or signature (just body)\n\n"
        "Example tone:\n"
        '"Hi [Name] — Just checking back regarding next steps for the [role] position. '
        "I remain very interested and would love to hear if there's any update. Thanks!\"\n\n"
        "Draft reply:"
    )

    # Generate draft with LLM
    draft_text = await generate_llm_text(prompt)

    # Fallback if LLM unavailable
    if not draft_text:
        # Extract first name from sender if possible
        sender_name = payload.sender.split()[0] if payload.sender else "there"
        draft_text = (
            f"Hi {sender_name} — Just checking back regarding next steps. "
            f"I remain very interested and would love to hear if there's any update. Thanks!"
        )

    return DraftReplyResponse(
        email_id=payload.email_id,
        draft=draft_text.strip(),
        sender=payload.sender,
        subject=payload.subject,
    )


# -------- helpers (MVP versions) --------

INTENTS_ALLOWED = [
    "summarize_activity",
    "list_bills_due",
    "list_suspicious",
    "list_followups",
    "list_interviews",
    "cleanup_promotions",
]

INTENT_MAP = {
    # chips / common phrasings → canonical intent names
    "summarize": "summarize_activity",
    "summary": "summarize_activity",
    "bills": "list_bills_due",
    "bill": "list_bills_due",
    "invoice": "list_bills_due",
    "suspicious": "list_suspicious",
    "phishing": "list_suspicious",
    "follow-up": "list_followups",
    "followups": "list_followups",
    "follow ups": "list_followups",
    "interview": "list_interviews",
    "interviews": "list_interviews",
    "unsubscribe": "cleanup_promotions",
    "clean promos": "cleanup_promotions",
    "promotions": "cleanup_promotions",
}


async def classify_intent(user_query: str) -> str:
    """
    Classify user intent with fallback chain:
    1. Fast keyword matching (INTENT_MAP)
    2. LLM classification (if keywords don't match)
    3. Safe fallback (summarize_activity)
    """
    q = (user_query or "").lower().strip()

    # 1. Fast keyword path (no LLM needed for common cases)
    for key, val in INTENT_MAP.items():
        if key in q:
            return val

    # 2. LLM fallback for more complex queries
    prompt = (
        "You are an intent classifier for an inbox assistant.\n"
        "User asked:\n"
        f"{q}\n\n"
        "Return EXACTLY one of these intents:\n"
        f"{', '.join(INTENTS_ALLOWED)}\n"
        "If unsure, use 'summarize_activity'. "
        "Return only the intent string, nothing else."
    )

    llm_guess = await generate_llm_text(prompt)
    if llm_guess:
        guess = llm_guess.strip().split()[0]
        if guess in INTENTS_ALLOWED:
            return guess

    # 3. Safe fallback
    return "summarize_activity"


async def generate_polished_summary(
    intent: str,
    base_summary: str,
    emails: list[dict],
    actions_performed: list[AssistantActionPerformed],
    mode: str,
    days: int,
) -> tuple[str, str]:
    """
    Use LLM to generate a more natural, user-friendly summary.
    Falls back to base_summary if LLM unavailable.

    Returns:
        Tuple of (summary_text, llm_used) where llm_used is "ollama", "openai", or "fallback"

    Safety: Only sends structured metadata, never raw email bodies.
    """
    # Build compact email preview (top 3 for context)
    top_emails = emails[:3]
    email_previews = []
    for e in top_emails:
        sender = e.get("sender", "Unknown")
        subject = e.get("subject", "No subject")[:50]
        risk = e.get("ml_category", "unknown")
        email_previews.append(f"- From: {sender}, Subject: {subject}..., Risk: {risk}")

    emails_block = (
        "\n".join(email_previews) if email_previews else "No emails to preview."
    )

    # Build actions transcript
    actions_block = ""
    if actions_performed:
        action_lines = []
        for act in actions_performed:
            status = "✓" if act.success else "✗"
            target = act.email_id or act.sender or "N/A"
            action_lines.append(f"{status} {act.action_type}: {target}")
        actions_block = "\n".join(action_lines)
    else:
        actions_block = "No actions performed."

    # Build LLM prompt
    prompt = (
        "You are an inbox assistant summarizing results for a user.\n"
        f"User asked about: {intent}\n"
        f"Time window: last {days} days\n"
        f"Mode: {mode} (run = actions executed, learn = just suggestions)\n\n"
        f"Base summary:\n{base_summary}\n\n"
        f"Top emails found:\n{emails_block}\n\n"
        f"Actions performed:\n{actions_block}\n\n"
        "Write a friendly, concise summary (2-3 sentences) that:\n"
        "- Explains what was found\n"
        "- Mentions any actions taken (if mode=run)\n"
        "- Sounds natural and helpful\n"
        "- Stays grounded in the data provided (no speculation)\n"
        "Return only the summary text, nothing else."
    )

    # Phase 3: Use new hybrid helper with guaranteed fallback
    summary, llm_used = await generate_assistant_text(
        kind="summary", prompt=prompt, fallback_template=base_summary
    )
    return (summary, llm_used)


async def run_intent_plan(intent: str, days: int, account: str):
    """
    Dispatch to an intent-specific planner that returns:
    {
      "summary": str,
      "emails": [ {id, sender, subject, timestamp, ...}, ... ],
      "suggested_actions": [ {label, kind, ...}, ... ]
    }
    """

    if intent == "list_bills_due":
        return await plan_list_bills_due(days=days, account=account)

    if intent == "list_suspicious":
        return await plan_list_suspicious(days=days, account=account)

    if intent == "list_followups":
        return await plan_list_followups(days=days, account=account)

    if intent == "list_interviews":
        return await plan_list_interviews(days=days, account=account)

    if intent == "cleanup_promotions":
        return await plan_cleanup_promotions(days=days, account=account)

    # default
    return await plan_summarize_activity(days=days, account=account)


# ----------------- intent planners -----------------


async def plan_list_bills_due(days: int, account: str) -> dict:
    """
    Find billing / invoice / payment due emails within the last N days.
    Return summary, emails[], suggested_actions[].
    """
    hits = []

    if ES_ENABLED:
        try:
            es = get_es_client()
            now = dt.datetime.utcnow()
            since = (now - dt.timedelta(days=days)).isoformat() + "Z"

            # Query for bills/invoices/receipts
            body = {
                "size": 10,
                "query": {
                    "bool": {
                        "filter": [
                            {"range": {"received_at": {"gte": since}}},
                        ],
                        "should": [
                            {"match": {"subject": "invoice"}},
                            {"match": {"subject": "bill"}},
                            {"match": {"subject": "payment due"}},
                            {"match": {"subject": "receipt"}},
                            {"match": {"body_text": "payment due"}},
                            {"match": {"body_text": "invoice"}},
                        ],
                        "minimum_should_match": 1,
                    }
                },
                "sort": [{"received_at": "asc"}],
                "_source": [
                    "message_id",
                    "gmail_id",
                    "from_addr",
                    "sender",
                    "subject",
                    "received_at",
                    "risk_score",
                    "body_text",
                ],
            }

            result = es.search(index=ES_INDEX, body=body)
            hits = result.get("hits", {}).get("hits", [])
        except Exception as e:
            print(f"[assistant] ES query failed for list_bills_due: {e}")

    emails = []
    for h in hits[:10]:
        src = h.get("_source", {})
        emails.append(
            {
                "id": src.get("message_id")
                or src.get("gmail_id")
                or h.get("_id", "unknown"),
                "sender": src.get("sender") or src.get("from_addr", ""),
                "subject": src.get("subject", ""),
                "timestamp": src.get("received_at", ""),
                "risk_score": src.get("risk_score", 0),
                "quarantined": src.get("quarantined", False),
                "amount": None,  # TODO: parse from body_text if available
                "due_date": None,  # TODO: parse from body_text if available
                "unsubscribe_candidate": False,
                "reply_needed": False,
            }
        )

    # Build human summary
    if emails:
        summary = f"You have {len(emails)} bills or invoices in the last {days}d."
        if len(emails) > 0:
            first = emails[0]
            summary += f" Most recent: {first['sender']} — {first['subject']}"
    else:
        summary = f"No upcoming bills found in the last {days}d."

    suggested_actions = []
    if emails:
        suggested_actions.append(
            {
                "label": "Review invoices and schedule payments",
                "kind": "follow_up",
                "email_id": emails[0]["id"],
            }
        )

    found_count = len(emails)
    next_steps = (
        "I can remind you about these or help you track payment deadlines."
        if found_count > 0
        else "No bills due soon. Want me to check older mail?"
    )
    followup_prompt = "Try: 'Show bills from last 60 days' or 'Find Stripe invoice.'"

    return {
        "summary": summary,
        "emails": emails,
        "suggested_actions": suggested_actions,
        "next_steps": next_steps,
        "followup_prompt": followup_prompt,
    }


async def plan_list_suspicious(days: int, account: str) -> dict:
    """
    High-risk or quarantined messages in last N days.
    """
    hits = []

    if ES_ENABLED:
        try:
            es = get_es_client()
            now = dt.datetime.utcnow()
            since = (now - dt.timedelta(days=days)).isoformat() + "Z"

            # Query for high-risk emails (risk_score >= 70 or quarantined)
            body = {
                "size": 10,
                "query": {
                    "bool": {
                        "filter": [
                            {"range": {"received_at": {"gte": since}}},
                        ],
                        "should": [
                            {"range": {"risk_score": {"gte": 70}}},
                            {"term": {"quarantined": True}},
                        ],
                        "minimum_should_match": 1,
                    }
                },
                "sort": [{"received_at": "desc"}],
                "_source": [
                    "message_id",
                    "gmail_id",
                    "from_addr",
                    "sender",
                    "subject",
                    "received_at",
                    "risk_score",
                    "quarantined",
                ],
            }

            result = es.search(index=ES_INDEX, body=body)
            hits = result.get("hits", {}).get("hits", [])
        except Exception as e:
            print(f"[assistant] ES query failed for list_suspicious: {e}")

    emails = []
    for h in hits[:10]:
        src = h.get("_source", {})
        emails.append(
            {
                "id": src.get("message_id")
                or src.get("gmail_id")
                or h.get("_id", "unknown"),
                "sender": src.get("sender") or src.get("from_addr", ""),
                "subject": src.get("subject", ""),
                "timestamp": src.get("received_at", ""),
                "risk_score": src.get("risk_score", 0),
                "quarantined": src.get("quarantined", False),
                "unsubscribe_candidate": False,
                "reply_needed": False,
            }
        )

    if emails:
        summary = (
            f"I found {len(emails)} suspicious / high-risk emails in the last {days}d."
        )
    else:
        summary = f"No suspicious emails in the last {days}d."

    suggested_actions = []
    if emails:
        suggested_actions.append(
            {
                "label": "Mark these as suspicious and quarantine them",
                "kind": "follow_up",
                "email_id": emails[0]["id"],
                "sender": emails[0]["sender"],
            }
        )

    found_count = len(emails)
    next_steps = (
        "I can quarantine these and prevent future emails from these senders."
        if found_count > 0
        else "Didn't see anything dangerous in your recent mail. 👍"
    )
    followup_prompt = "Try: 'Show all quarantined messages' or 'Scan last 60 days.'"

    return {
        "summary": summary,
        "emails": emails,
        "suggested_actions": suggested_actions,
        "next_steps": next_steps,
        "followup_prompt": followup_prompt,
    }


async def plan_list_followups(days: int, account: str) -> dict:
    """
    Threads waiting on the user (recruiters, hiring loops, nudges like 'checking in?').
    """
    hits = []

    if ES_ENABLED:
        try:
            es = get_es_client()
            now = dt.datetime.utcnow()
            since = (now - dt.timedelta(days=days)).isoformat() + "Z"

            # Query for follow-up indicators
            body = {
                "size": 10,
                "query": {
                    "bool": {
                        "filter": [
                            {"range": {"received_at": {"gte": since}}},
                        ],
                        "should": [
                            {"match_phrase": {"subject": "follow up"}},
                            {"match_phrase": {"subject": "checking in"}},
                            {"match_phrase": {"subject": "following up"}},
                            {"match_phrase": {"subject": "next steps"}},
                            {"match_phrase": {"subject": "still interested"}},
                            {"match_phrase": {"body_text": "checking in"}},
                            {"match_phrase": {"body_text": "following up"}},
                            {"match_phrase": {"body_text": "waiting to hear"}},
                            {"match": {"sender": "recruiter"}},
                            {"match": {"sender": "hiring"}},
                        ],
                        "minimum_should_match": 1,
                    }
                },
                "sort": [{"received_at": "desc"}],
                "_source": [
                    "message_id",
                    "gmail_id",
                    "from_addr",
                    "sender",
                    "subject",
                    "received_at",
                    "risk_score",
                ],
            }

            result = es.search(index=ES_INDEX, body=body)
            hits = result.get("hits", {}).get("hits", [])
        except Exception as e:
            print(f"[assistant] ES query failed for list_followups: {e}")

    emails = []
    for h in hits[:10]:
        src = h.get("_source", {})
        emails.append(
            {
                "id": src.get("message_id")
                or src.get("gmail_id")
                or h.get("_id", "unknown"),
                "sender": src.get("sender") or src.get("from_addr", ""),
                "sender_email": src.get("from_addr", ""),  # Add actual email address
                "subject": src.get("subject", ""),
                "timestamp": src.get("received_at", ""),
                "risk_score": src.get("risk_score", 0),
                "quarantined": src.get("quarantined", False),
                "unsubscribe_candidate": False,
                "reply_needed": True,  # this is the whole point of followups
            }
        )

    if emails:
        summary = f"{len(emails)} conversation(s) are waiting on you to reply."
    else:
        summary = f"No open follow-ups detected in the last {days}d."

    suggested_actions = []
    if emails:
        # Add draft_reply action for each follow-up email
        for email in emails[:3]:  # Limit to top 3 for UI clarity
            suggested_actions.append(
                {
                    "label": f"Draft reply to {email['sender']}",
                    "kind": "draft_reply",
                    "email_id": email["id"],
                    "sender": email["sender"],
                    "sender_email": email["sender_email"],  # Add email address
                    "subject": email["subject"],
                }
            )

    found_count = len(emails)
    next_steps = (
        "Click Draft Reply and I'll write a short nudge you can send in Gmail."
        if found_count > 0
        else "No one's waiting on you. Want to send thank-you notes instead?"
    )
    followup_prompt = "Try: 'Draft a thank-you to Acme recruiter' or 'Follow up with the Stripe loop.'"

    return {
        "summary": summary,
        "emails": emails,
        "suggested_actions": suggested_actions,
        "next_steps": next_steps,
        "followup_prompt": followup_prompt,
    }


async def plan_list_interviews(days: int, account: str) -> dict:
    """
    Interview invites / scheduling / next-step emails.
    """
    hits = []

    if ES_ENABLED:
        try:
            es = get_es_client()
            now = dt.datetime.utcnow()
            since = (now - dt.timedelta(days=days)).isoformat() + "Z"

            # Query for interview-related content
            body = {
                "size": 10,
                "query": {
                    "bool": {
                        "filter": [
                            {"range": {"received_at": {"gte": since}}},
                        ],
                        "should": [
                            {"match": {"subject": "interview"}},
                            {"match": {"subject": "onsite"}},
                            {"match": {"subject": "phone screen"}},
                            {"match": {"subject": "schedule a call"}},
                            {"match": {"subject": "loop"}},
                            {"match": {"subject": "technical interview"}},
                            {"match_phrase": {"body_text": "interview"}},
                            {"match_phrase": {"body_text": "schedule"}},
                            {"match_phrase": {"body_text": "phone screen"}},
                        ],
                        "minimum_should_match": 1,
                    }
                },
                "sort": [{"received_at": "desc"}],
                "_source": [
                    "message_id",
                    "gmail_id",
                    "from_addr",
                    "sender",
                    "subject",
                    "received_at",
                    "risk_score",
                ],
            }

            result = es.search(index=ES_INDEX, body=body)
            hits = result.get("hits", {}).get("hits", [])
        except Exception as e:
            print(f"[assistant] ES query failed for list_interviews: {e}")

    emails = []
    for h in hits[:10]:
        src = h.get("_source", {})
        emails.append(
            {
                "id": src.get("message_id")
                or src.get("gmail_id")
                or h.get("_id", "unknown"),
                "sender": src.get("sender") or src.get("from_addr", ""),
                "subject": src.get("subject", ""),
                "timestamp": src.get("received_at", ""),
                "risk_score": src.get("risk_score", 0),
                "quarantined": src.get("quarantined", False),
                "unsubscribe_candidate": False,
                "reply_needed": True,
            }
        )

    if emails:
        summary = f"{len(emails)} interview-related thread(s) in the last {days}d."
    else:
        summary = f"No interview invites found in the last {days}d."

    suggested_actions = []
    if emails:
        suggested_actions.append(
            {
                "label": "Add to Tracker",
                "kind": "follow_up",
                "email_id": emails[0]["id"],
            }
        )

    found_count = len(emails)
    next_steps = (
        "Click 'Add to Tracker' to log these loops and track your pipeline."
        if found_count > 0
        else "No interview invites recently. Try searching 60 days back?"
    )
    followup_prompt = "Try: 'Show interviews from last 60 days' or 'Find Stripe loop.'"

    return {
        "summary": summary,
        "emails": emails,
        "suggested_actions": suggested_actions,
        "next_steps": next_steps,
        "followup_prompt": followup_prompt,
    }


async def plan_cleanup_promotions(days: int, account: str) -> dict:
    """
    Bulk/promo/newsletter content. Candidates for unsubscribe/mute.
    """
    hits = []

    if ES_ENABLED:
        try:
            es = get_es_client()
            now = dt.datetime.utcnow()
            since = (now - dt.timedelta(days=days)).isoformat() + "Z"

            # Query for promotional emails
            body = {
                "size": 20,
                "query": {
                    "bool": {
                        "filter": [
                            {"range": {"received_at": {"gte": since}}},
                        ],
                        "should": [
                            {"term": {"label": "CATEGORY_PROMOTIONS"}},
                            {"term": {"labels": "CATEGORY_PROMOTIONS"}},
                            {"match": {"subject": "unsubscribe"}},
                            {"match": {"body_text": "unsubscribe"}},
                        ],
                        "minimum_should_match": 1,
                    }
                },
                "sort": [{"received_at": "desc"}],
                "_source": [
                    "message_id",
                    "gmail_id",
                    "from_addr",
                    "sender",
                    "subject",
                    "received_at",
                    "risk_score",
                ],
            }

            result = es.search(index=ES_INDEX, body=body)
            hits = result.get("hits", {}).get("hits", [])
        except Exception as e:
            print(f"[assistant] ES query failed for cleanup_promotions: {e}")

    emails = []
    for h in hits[:20]:
        src = h.get("_source", {})
        sender_addr = src.get("sender") or src.get("from_addr", "")
        emails.append(
            {
                "id": src.get("message_id")
                or src.get("gmail_id")
                or h.get("_id", "unknown"),
                "sender": sender_addr,
                "subject": src.get("subject", ""),
                "timestamp": src.get("received_at", ""),
                "risk_score": src.get("risk_score", 0),
                "quarantined": src.get("quarantined", False),
                "unsubscribe_candidate": True,
                "reply_needed": False,
            }
        )

    if emails:
        summary = (
            f"I found {len(emails)} promotional / bulk emails in the last {days}d. "
            "I can mute these senders for you."
        )
    else:
        summary = f"No obvious promo/blast senders found in the last {days}d."

    suggested_actions = []
    if emails:
        suggested_actions.append(
            {
                "label": f"Unsubscribe from {emails[0]['sender']}",
                "kind": "unsubscribe",
                "sender": emails[0]["sender"],
            }
        )

    found_count = len(emails)
    next_steps = (
        "I can mute these senders or help you unsubscribe from their lists."
        if found_count > 0
        else "Your inbox looks pretty clean. No bulk senders to mute."
    )
    followup_prompt = "Try: 'Show all newsletters' or 'Mute LinkedIn emails.'"

    return {
        "summary": summary,
        "emails": emails,
        "suggested_actions": suggested_actions,
        "next_steps": next_steps,
        "followup_prompt": followup_prompt,
    }


async def plan_summarize_activity(days: int, account: str) -> dict:
    """
    High-level digest. We *call the other planners* but with tight limits,
    and then stitch a summary string.
    """
    bills = await plan_list_bills_due(days=days, account=account)
    sus = await plan_list_suspicious(days=days, account=account)
    foll = await plan_list_followups(days=days, account=account)
    ivs = await plan_list_interviews(days=days, account=account)

    summary_parts = []
    if bills["emails"]:
        summary_parts.append(f"{len(bills['emails'])} bill(s) due soon")
    if sus["emails"]:
        summary_parts.append(f"{len(sus['emails'])} suspicious senders")
    if foll["emails"]:
        summary_parts.append(f"{len(foll['emails'])} waiting on you to reply")
    if ivs["emails"]:
        summary_parts.append(f"{len(ivs['emails'])} interview invite(s)")

    if summary_parts:
        summary = "Here's what matters: " + ", ".join(summary_parts) + "."
    else:
        summary = f"In the last {days}d: nothing urgent detected — no bills, risks, interviews, or pending follow-ups."

    # For summarize_activity, we don't need to dump all emails (we can return empty list for now).
    suggested_actions = []
    if sus["emails"]:
        suggested_actions.append(
            {
                "label": "Review suspicious email(s)",
                "kind": "follow_up",
                "email_id": sus["emails"][0]["id"],
            }
        )

    # Smart next_steps based on what's active
    has_activity = len(summary_parts) > 0
    if has_activity:
        next_steps = "Focus on follow-ups first — click Draft Reply for quick nudges."
    else:
        next_steps = "Nothing urgent right now. Want to review older threads (60d) or clean up promos?"
    followup_prompt = "Try: 'Show follow-ups from 60 days' or 'Clean up newsletters.'"

    return {
        "summary": summary,
        "emails": [],
        "suggested_actions": suggested_actions,
        "next_steps": next_steps,
        "followup_prompt": followup_prompt,
    }


async def update_sender_memory(
    emails: list[dict],
    intent: str,
    memory_opt_in: bool,
    account: str,
    BASE_INTERNAL_API: str,
) -> list[AssistantActionPerformed]:
    """
    Persist long-term trust / mute rules for senders.
    We call the same /api/settings/senders endpoints the Settings page uses.

    Behavior:
    - For cleanup_promotions: mark sender as muted (auto-archive future promos)
    - For 'safe' cases (future work): mark sender as safe

    Returns AssistantActionPerformed[] entries describing what we stored.
    """

    results: list[AssistantActionPerformed] = []
    if not memory_opt_in:
        return results  # user didn't allow memory, skip

    # Helper for POST
    async def _post_json(path: str, payload: Dict[str, Any]) -> tuple[bool, str]:
        url = f"{BASE_INTERNAL_API}{path}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code >= 200 and resp.status_code < 300:
                return True, "ok"
            return False, f"http {resp.status_code}"
        except Exception as e:
            return False, f"error: {e}"

    # (A) Promotions cleanup → mute sender
    if intent == "cleanup_promotions":
        # For every promo email with unsubscribe_candidate = True,
        # call POST /api/settings/senders/mute { sender }
        seen = set()
        for em in emails:
            if not em.get("unsubscribe_candidate"):
                continue
            sender_addr = em.get("sender", "")
            if not sender_addr or sender_addr in seen:
                continue
            seen.add(sender_addr)

            ok, status = await _post_json(
                "/api/settings/senders/mute",
                {"sender": sender_addr},
            )

            results.append(
                AssistantActionPerformed(
                    type="memory.mute_sender",
                    status=status,
                    target=sender_addr,
                )
            )

    # (B) Future path: auto-safe trusted senders.
    # e.g. if we later add plan logic that marks a sender as "safe_candidate": True,
    # we'd POST /api/settings/senders/safe { sender } here.

    return results


async def maybe_apply_bulk_actions(
    intent: str,
    fetched: dict,
    account: str,
    memory_opt_in: bool,
) -> list[AssistantActionPerformed]:
    """
    If mode == "run", attempt to actually apply actions to the user's inbox.
    Uses the same endpoints that Inbox Actions uses:
      - POST /api/actions/unsubscribe
      - POST /api/actions/mark_safe
      - POST /api/actions/mark_suspicious
      - POST /api/actions/archive

    We will:
    - Look at fetched["emails"]
    - Infer what to do for each intent
    - Call the right endpoint for each email/sender
    - Collect a list of AssistantActionPerformed for the transcript

    NOTE:
    - We're assuming this FastAPI service is reachable at the same base (nginx forwards /api/*).
      Inside the container we can usually hit http://localhost:8003 since that's where uvicorn runs.
      If that's different in prod, update BASE_INTERNAL_API accordingly.
    """

    BASE_INTERNAL_API = os.getenv(
        "ASSISTANT_INTERNAL_API_BASE", "http://localhost:8003"
    )

    results: list[AssistantActionPerformed] = []

    # Helper to safely POST to our own API
    async def _post_json(path: str, payload: Dict[str, Any]) -> tuple[bool, str]:
        url = f"{BASE_INTERNAL_API}{path}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code >= 200 and resp.status_code < 300:
                return True, "ok"
            else:
                return False, f"http {resp.status_code}"
        except Exception as e:
            return False, f"error: {e}"

    # Intent-specific action policies:
    #
    # cleanup_promotions:
    #   - for each email with unsubscribe_candidate==True:
    #       * call POST /api/actions/unsubscribe { message_id }
    #
    # list_suspicious:
    #   - for each email with risk_score >= 70 or quarantined==True:
    #       * call POST /api/actions/mark_suspicious { message_id }
    #
    # list_followups:
    #   (Phase 1.2: No direct mutation. We might draft replies in future.)
    #
    # list_bills_due:
    #   (Phase 1.2: No direct mutation. Billing is FYI only.)
    #
    # list_interviews:
    #   (Phase 1.2: No direct mutation. Could add to Tracker in future.)
    #
    # summarize_activity:
    #   (Phase 1.2: No bulk actions; it's just a digest.)

    emails = fetched.get("emails", [])

    if intent == "cleanup_promotions":
        # Try unsubscribing and/or archiving promo senders
        for em in emails:
            if not em.get("unsubscribe_candidate"):
                continue
            msg_id = em.get("id")
            if not msg_id:
                continue

            ok, status = await _post_json(
                "/api/actions/unsubscribe",
                {"message_id": msg_id},
            )

            results.append(
                AssistantActionPerformed(
                    type="unsubscribe",
                    status=status,
                    target=em.get("sender", ""),
                )
            )

            # Optional follow-up: archive after unsubscribe
            ok2, status2 = await _post_json(
                "/api/actions/archive",
                {"message_id": msg_id},
            )
            results.append(
                AssistantActionPerformed(
                    type="archive",
                    status=status2,
                    target=msg_id,
                )
            )

    elif intent == "list_suspicious":
        # Quarantine high-risk emails
        for em in emails:
            msg_id = em.get("id")
            if not msg_id:
                continue

            high_risk = (em.get("risk_score", 0) >= 70) or em.get("quarantined", False)
            if not high_risk:
                continue

            ok, status = await _post_json(
                "/api/actions/mark_suspicious",
                {"message_id": msg_id},
            )

            results.append(
                AssistantActionPerformed(
                    type="mark_suspicious",
                    status=status,
                    target=msg_id,
                )
            )

    # For other intents, we currently don't mutate in Phase 1.2.
    # We still return any results we gathered.

    # Phase 1.3: update memory (sender overrides) if allowed.
    memory_results = await update_sender_memory(
        emails=emails,
        intent=intent,
        memory_opt_in=memory_opt_in,
        account=account,
        BASE_INTERNAL_API=BASE_INTERNAL_API,
    )

    # merge memory results into results
    results.extend(memory_results)
    return results
