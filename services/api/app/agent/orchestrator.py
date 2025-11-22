"""
Agent v2 - MailboxAgentOrchestrator

Coordinates:
1. Intent classification (rule-based + LLM fallback)
2. Tool planning (which tools to call, in what order)
3. Tool execution (with timeouts + fallbacks)
4. LLM synthesis (generate final answer from tool results)
"""

from typing import List, Dict, Any, Optional, Tuple, Literal
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas_agent import (
    AgentRunRequest,
    AgentRunResponse,
    AgentCard,
    ToolResult,
    AgentMetrics,
)
from app.agent.tools import ToolRegistry
from app.agent.metrics import record_agent_run, record_tool_call
from app.agent.rag import retrieve_email_contexts, retrieve_kb_contexts
from app.agent.answering import complete_agent_answer, merge_cards_with_llm
from app.es import ES_URL, ES_ENABLED
from elasticsearch import AsyncElasticsearch

logger = logging.getLogger(__name__)

# Intent types for deterministic classification
MailboxIntent = Literal[
    "suspicious",
    "bills",
    "interviews",
    "followups",
    "profile",
    "clean_promos",
    "unsubscribe",
    "generic",
]


@dataclass
class IntentSpec:
    """Specification for intent-driven behavior contract."""

    name: MailboxIntent
    default_time_window_days: int
    tools: List[str]
    require_counts: bool
    # How to treat zero-results vs non-zero
    zero_title: Optional[str] = None
    nonzero_title: Optional[str] = None


# Intent specifications - defines the behavior contract for each intent
INTENT_SPECS: Dict[MailboxIntent, IntentSpec] = {
    "suspicious": IntentSpec(
        name="suspicious",
        default_time_window_days=30,
        tools=["email_search", "security_scan"],
        require_counts=True,
        zero_title="No Suspicious Emails Found",
        nonzero_title="Suspicious Emails Found",
    ),
    "followups": IntentSpec(
        name="followups",
        default_time_window_days=30,
        tools=["email_search"],
        require_counts=True,
        zero_title="No Conversations Need Follow-up",
        nonzero_title="Conversations Waiting on Your Reply",
    ),
    "bills": IntentSpec(
        name="bills",
        default_time_window_days=60,
        tools=["email_search", "bill_parser"],
        require_counts=True,
        zero_title="No Bills Found",
        nonzero_title="Bills Overview",
    ),
    "interviews": IntentSpec(
        name="interviews",
        default_time_window_days=30,
        tools=["email_search"],
        require_counts=True,
        zero_title="No Interviews Found",
        nonzero_title="Interview Schedule",
    ),
    "clean_promos": IntentSpec(
        name="clean_promos",
        default_time_window_days=30,
        tools=["email_search", "unsubscribe_finder"],
        require_counts=True,
        zero_title="No Promotional Emails Found",
        nonzero_title="Promotions & Newsletters",
    ),
    "unsubscribe": IntentSpec(
        name="unsubscribe",
        default_time_window_days=60,
        tools=["email_search", "unsubscribe_finder"],
        require_counts=True,
        zero_title="No Unopened Newsletters",
        nonzero_title="Unsubscribe from Unopened Newsletters",
    ),
    "profile": IntentSpec(
        name="profile",
        default_time_window_days=60,
        tools=["email_search", "applications_lookup"],
        require_counts=True,
        zero_title="Your Application Profile",
        nonzero_title="Your Application Profile",
    ),
    "generic": IntentSpec(
        name="generic",
        default_time_window_days=30,
        tools=["email_search"],
        require_counts=False,
        zero_title=None,
        nonzero_title=None,
    ),
}

# Shared style guidelines for all intent prompts
SHARED_STYLE_HINT = (
    "\nGeneral style rules for all answers:\n"
    "- Explicitly mention: (a) how many emails were scanned, and (b) what time window you looked at "
    "if that information is available from the tools.\n"
    "- Always keep your answer under ~180 words.\n"
    "- Prefer short paragraphs and bullet lists over long text.\n"
    "- If nothing relevant was found, say so clearly and briefly, and suggest how the user might refine the query.\n"
)

# Intent-specific style hints for zero vs non-zero results
INTENT_STYLE_HINTS: Dict[str, str] = {
    "suspicious": """
You are checking for suspicious or phishing emails.

If metrics.matches == 0:
- Start with "No suspicious emails were identified in your inbox over the last {time_window_days} days."
- Then give 1–2 concise vigilance tips.

If metrics.matches > 0:
- Start with "I found {matches} emails that look suspicious out of {emails_scanned} scanned."
- Mention 1–2 patterns (e.g., fake invoices, urgent payment requests).
""",
    "followups": """
You are helping find conversations needing follow-up.

If count == 0:
- Start with "You're caught up — no conversations are currently waiting on your reply."
- Suggest checking back later.

If count > 0:
- Start with "You have {count} conversations waiting for your reply in the last {time_window_days} days."
- Highlight top 3-5 by priority.
""",
    "bills": """
You are analyzing bills and invoices.

If total == 0:
- Start with "No recent bills found in your inbox for the last {time_window_days} days."
- Keep it brief.

If total > 0:
- Start with "I found {total_bills} bills in the last {time_window_days} days: {due_soon} due soon, {overdue} overdue, and {other} upcoming or paid."
- Break down by sections.
""",
    "interviews": """
You are tracking interview-related emails.

If total == 0:
- Start with "No interview-related emails found in the last {time_window_days} days."

If total > 0:
- Start with "You have {upcoming} upcoming interviews, {awaiting_confirmation} needing a response, and {past} completed in the last {time_window_days} days."
""",
    "clean_promos": """
You are identifying promotional emails for cleanup.

If count == 0:
- Start with "No promotional senders found cluttering your inbox."

If count > 0:
- Start with "I found {promo_count} promotional senders cluttering your inbox."
- In preview mode, clarify nothing was changed yet.
""",
}

# Intent-specific system prompts for LLM synthesis
INTENT_SYSTEM_PROMPTS: Dict[str, str] = {
    "suspicious": (
        "You are ApplyLens's email security assistant.\n"
        "The user is looking for potentially risky or scam emails in their job-search inbox.\n"
        "\n"
        "IMPORTANT: You ALWAYS have access to tool results with real data:\n"
        "- Counts of emails scanned and suspicious matches\n"
        "- Sender domains, subjects, risk labels, and specific reasons\n"
        "- Time window (e.g., last 7/30/60 days)\n"
        "\n"
        "Write responses that are:\n"
        "- Short (1–2 short paragraphs max) plus a compact bullet list.\n"
        "- Concrete and grounded in the tool data (domains, subjects, links, risk scores).\n"
        "- Actionable: tell the user exactly what to do next (ignore, delete, report, or reply carefully).\n"
        "\n"
        "When you describe risky emails:\n"
        "- ALWAYS explicitly mention how many emails were scanned and how many were flagged as potentially suspicious.\n"
        "- Explain WHY they were flagged using 2–4 bullet points (e.g., unfamiliar domains, urgent payment requests, login prompts, strange attachments/links).\n"
        "- Emphasize they are 'potentially' suspicious and should be reviewed.\n"
        "- DO NOT say you have 'no context' or 'cannot assess their legitimacy' - you have the tool results!\n"
        "- Instead, use language like: 'these are flagged based on the signals above; they may include false positives, so review them before taking action.'\n"
        "\n"
        "Format your answer EXACTLY as:\n"
        "1. A short opening sentence that includes how many emails you scanned and what time window.\n"
        "2. A section heading '**Key red flags:**' with 2–4 bullet points explaining WHY emails were flagged (or write 'None found' if there are no suspicious emails).\n"
        "3. A section heading '**Safe next steps:**' with 2–4 bullet points of concrete recommendations.\n"
    )
    + SHARED_STYLE_HINT,
    "bills": (
        "You are ApplyLens's billing assistant.\n"
        "The user wants an overview of bills and invoices in their inbox.\n"
        "\n"
        "Write responses that are:\n"
        "- Focused on due dates, amounts, and senders.\n"
        "- Grouped into 'due soon', 'overdue', and 'other' when possible.\n"
        "- Short: a 1-paragraph summary, then a small list of the most important bills.\n"
        "\n"
        "Format your answer EXACTLY as:\n"
        "1. A short opening sentence that includes how many bills/invoices you scanned and what time window.\n"
        "2. Three subsections: '**Due soon:**', '**Overdue:**', and '**Other:**'. "
        "If a section is empty, write 'None' for that section.\n"
    )
    + SHARED_STYLE_HINT,
    "interviews": (
        "You are ApplyLens's interview assistant.\n"
        "The user wants help understanding recruiter and interview-related emails.\n"
        "\n"
        "Write responses that are:\n"
        "- Organized into sections: 'Upcoming interviews', 'Waiting on recruiter', 'Closed / done'.\n"
        "- Specific about company, role, date/time, and what the user should do next.\n"
        "- Brief: 1–2 paragraphs plus a bullet list of concrete next actions.\n"
        "\n"
        "Format your answer EXACTLY as:\n"
        "1. A short opening sentence that includes how many interview/recruiter emails you scanned and what time window.\n"
        "2. Three subsections: '**Upcoming interviews:**', '**Waiting on recruiter:**', and '**Closed / done:**'. "
        "Under each section, list at most 3 items with company, role, and what to do next. "
        "If a section is empty, write 'None' for that section.\n"
    )
    + SHARED_STYLE_HINT,
    "followups": (
        "You are ApplyLens's follow-up assistant.\n"
        "The user wants to know where they should send a follow-up email.\n"
        "\n"
        "Write responses that are:\n"
        "- Prioritized: show the top 3–5 highest-impact follow-ups first.\n"
        "- Specific: include company, role, last email date, and suggested follow-up angle.\n"
        "- Concise: one short paragraph and then a numbered list of suggested follow-ups.\n"
        "\n"
        "Format your answer EXACTLY as:\n"
        "1. A short opening sentence that includes how many threads you scanned and what time window.\n"
        "2. A numbered list of the top 3–5 follow-ups, each with company, role, last contact date, and a suggested follow-up angle. "
        "If there are no follow-ups needed, write 'None needed at this time' and suggest checking back later.\n"
    )
    + SHARED_STYLE_HINT,
    "profile": (
        "You are ApplyLens's mailbox analyst.\n"
        "You summarize the user's job-search mailbox activity and risk profile.\n"
        "\n"
        "Write responses that are:\n"
        "- Quantitative: mention total emails, emails in the recent window, and rough label/risk breakdowns.\n"
        "- High level: focus on trends, not individual messages.\n"
        "- Short: one overview paragraph plus 3–5 bullet points of key insights.\n"
        "\n"
        "Only mention security risk if the risk buckets show non-trivial medium/high/critical values.\n"
        "\n"
        "Format your answer EXACTLY as:\n"
        "1. A short opening sentence that includes total email volume and the time window analyzed.\n"
        "2. 3–5 bullet points for key stats (applications, recruiter replies, interviews, any non-trivial security risk). "
        "If a category has zero activity, you may omit it from the bullets.\n"
        "\n"
        "CRITICAL - Card output rules:\n"
        '- Always use "kind": "generic_summary" for profile cards.\n'
        '- NEVER use "profile_summary" or any other string for the kind field.\n'
        '- Allowed kinds are ONLY: "suspicious_summary", "bills_summary", "interviews_summary", "followups_summary", "thread_list", "generic_summary", "error".\n'
    )
    + SHARED_STYLE_HINT,
    "generic": (
        "You are ApplyLens's mailbox assistant.\n"
        "You help the user understand and manage their job-search inbox.\n"
        "\n"
        "Write responses that are:\n"
        "- Grounded in the tool data (emails, stats) and never fabricated.\n"
        "- Short and practical: 1 paragraph plus a bullet list of suggested actions.\n"
        "- Focused on prioritization: what should the user read or act on next.\n"
        "\n"
        "Format your answer EXACTLY as:\n"
        "1. A short opening sentence that includes how many emails you found and what time window.\n"
        "2. A bullet list of 3–5 concrete next actions the user should take. "
        "If nothing was found, suggest how the user could refine their query.\n"
    )
    + SHARED_STYLE_HINT,
}


def classify_intent(query: str) -> str:
    """
    Classify user intent from query using deterministic keyword matching.

    This is deliberately deterministic so Playwright tests can force
    a given intent by including key words in the query.

    Returns: "suspicious" | "bills" | "interviews" | "followups" | "profile" | "generic"
    """
    q = query.lower()

    # Check more specific intents first to avoid false matches

    if "suspicious" in q or "scam" in q or "phishing" in q or "fraud" in q:
        return "suspicious"

    if "bill" in q or "bills" in q or "invoice" in q or "invoices" in q:
        return "bills"

    # Check for follow-ups BEFORE interviews (since queries may contain both)
    if "follow up" in q or "follow-up" in q or "followups" in q or "follow ups" in q:
        return "followups"

    if "interview" in q or "recruiter" in q or "hiring manager" in q:
        return "interviews"

    # Profile/stats queries
    if "profile" in q or "stats" in q or "statistics" in q or "overview" in q:
        return "profile"

    # fallback
    return "generic"


def build_llm_messages(
    intent: str,
    query: str,
    tool_results: List[ToolResult],
) -> List[Dict[str, str]]:
    """
    Convert intent + tool outputs into a chat-style message list for the LLM.

    Provides intent-specific system prompts and tool context summaries.
    """
    system_prompt = INTENT_SYSTEM_PROMPTS.get(intent, INTENT_SYSTEM_PROMPTS["generic"])

    # Track primary email_search results for explicit count requirement
    primary_total = None
    primary_window_days = None

    # Build a compact, LLM-friendly summary of tool outputs.
    tool_summaries: List[str] = []
    for tr in tool_results:
        if tr.status != "success":
            continue
        name = tr.tool_name
        data = tr.data or {}

        if name == "email_search":
            total = data.get("total") or data.get("total_found") or 0
            # Extract time window from multiple possible locations
            window_days = None
            if "time_window_days" in data:
                window_days = data["time_window_days"]
            elif "time_window" in data:
                tw = data["time_window"]
                if isinstance(tw, dict):
                    window_days = tw.get("days")
                elif isinstance(tw, (int, float)):
                    window_days = tw

            # Capture first email_search for explicit count requirement
            if primary_total is None:
                primary_total = total
                primary_window_days = window_days

            label = f"{total} matching emails"
            if window_days:
                label += f" in the last {window_days} days"
            tool_summaries.append(f"- email_search: {label}.")

        elif name == "security_scan":
            suspicious = (
                data.get("suspicious_count") or data.get("suspicious_emails") or 0
            )
            risky_domains = data.get("risky_domains") or []
            dom_label = ", ".join(risky_domains[:5]) if risky_domains else "none"
            tool_summaries.append(
                f"- security_scan: {suspicious} suspicious emails; risky domains: {dom_label}."
            )

        elif name == "thread_detail":
            emails = data.get("emails") or []
            tid = data.get("thread_id")
            tool_summaries.append(
                f"- thread_detail: {len(emails)} messages in thread {tid!r}."
            )

        elif name == "applications_lookup":
            apps = data.get("applications") or []
            tool_summaries.append(
                f"- applications_lookup: {len(apps)} applications linked to these emails."
            )

        elif name == "profile_stats":
            total = data.get("total_emails")
            window_total = data.get("total_in_window")
            days = data.get("time_window_days")
            tool_summaries.append(
                f"- profile_stats: {total} total emails; {window_total} in the last {days} days."
            )

    condensed_context = (
        "Here is a concise summary of the tools that were called and what they found:\n"
        + "\n".join(tool_summaries)
        if tool_summaries
        else "No relevant tool data was available for this query.\n"
    )

    # Add explicit count requirement if we have email_search data
    count_requirement = ""
    if primary_total is not None and primary_window_days is not None:
        count_requirement = (
            f"For this answer, you scanned approximately {primary_total} emails "
            f"in the last {primary_window_days} days.\n"
            "Your first sentence MUST explicitly mention how many emails were scanned "
            "and what time window you looked at.\n\n"
        )

    user_instructions = (
        f"User query:\n{query}\n\n"
        f"{count_requirement}"
        "Use the summary of tool results above to answer the question.\n"
        "Do NOT restate the raw tool data exhaustively; instead, summarize and prioritize.\n"
        "If the tools indicate there is nothing relevant, say that clearly.\n"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": condensed_context},
        {"role": "user", "content": user_instructions},
    ]


class MailboxAgentOrchestrator:
    """
    Orchestrates mailbox agent runs.

    Responsibilities:
    - Parse user query → detect intent
    - Plan tool execution
    - Execute tools with fallbacks
    - Synthesize LLM answer
    - Build response cards
    """

    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        self.tools = tool_registry or ToolRegistry()

    async def _load_prefs_for_user(
        self, db: Optional[AsyncSession], user_id: str
    ) -> Dict[str, Any]:
        """
        Load user preferences from agent_preferences table.

        Returns a dict like:
        {
            "suspicious": {"blocked_thread_ids": [...]},
            "followups": {"done_thread_ids": [...], "hidden_thread_ids": [...]},
            "bills": {"autopay_thread_ids": [...]}
        }

        If no preferences found or db is None, returns empty dict.
        """
        if not db:
            return {}

        try:
            from app.models import AgentPreferences

            result = await db.execute(
                select(AgentPreferences).where(AgentPreferences.user_id == user_id)
            )
            row = result.scalar_one_or_none()
            return row.data if row else {}
        except Exception as e:
            logger.warning(f"Failed to load preferences for user {user_id}: {e}")
            return {}

    def _filter_tool_results_by_preferences(
        self, tool_results: List[ToolResult], intent: str, prefs: Dict[str, Any]
    ) -> List[ToolResult]:
        """
        Filter tool results based on user preferences.

        Intent-specific filtering:
        - suspicious: Remove threads in blocked_thread_ids
        - followups: Remove threads in done_thread_ids or hidden_thread_ids
        - bills: Remove threads in autopay_thread_ids

        Returns filtered list of tool results.
        """
        if not prefs:
            return tool_results

        if intent == "suspicious":
            blocked = set(prefs.get("suspicious", {}).get("blocked_thread_ids", []))
            if blocked:
                original_count = len(tool_results)
                tool_results = [
                    r
                    for r in tool_results
                    if not hasattr(r, "thread_id") or r.thread_id not in blocked
                ]
                filtered_count = original_count - len(tool_results)
                if filtered_count > 0:
                    logger.info(
                        f"Filtered {filtered_count} suspicious results based on user preferences"
                    )

        elif intent == "followups":
            done_ids = set(prefs.get("followups", {}).get("done_thread_ids", []))
            hidden_ids = set(prefs.get("followups", {}).get("hidden_thread_ids", []))
            all_filtered = done_ids | hidden_ids
            if all_filtered:
                original_count = len(tool_results)
                tool_results = [
                    r
                    for r in tool_results
                    if not hasattr(r, "thread_id") or r.thread_id not in all_filtered
                ]
                filtered_count = original_count - len(tool_results)
                if filtered_count > 0:
                    logger.info(
                        f"Filtered {filtered_count} followup results based on user preferences"
                    )

        elif intent == "bills":
            autopay_ids = set(prefs.get("bills", {}).get("autopay_thread_ids", []))
            if autopay_ids:
                original_count = len(tool_results)
                tool_results = [
                    r
                    for r in tool_results
                    if not hasattr(r, "thread_id") or r.thread_id not in autopay_ids
                ]
                filtered_count = original_count - len(tool_results)
                if filtered_count > 0:
                    logger.info(
                        f"Filtered {filtered_count} bill results based on user preferences"
                    )

        return tool_results

    async def run(
        self, request: AgentRunRequest, db: Optional[AsyncSession] = None
    ) -> AgentRunResponse:
        """
        Execute a complete agent run.

        Flow:
        1. Classify intent (deterministic keyword-based)
        2. Plan tools (intent-specific tool selection)
        3. Execute tools (parallel where possible)
        4. Synthesize answer with LLM + RAG
        5. Build cards from tool results
        6. Record metrics
        """
        start_time = datetime.utcnow()

        try:
            # 1. Classify intent (or use explicit override from request)
            if request.intent:
                intent = request.intent
                logger.info(
                    f"Agent run: query='{request.query}', intent='{intent}' (explicit)"
                )
            else:
                intent = classify_intent(request.query)
                logger.info(
                    f"Agent run: query='{request.query}', intent='{intent}' (classified)"
                )

            # 2. Plan tool execution based on intent
            tool_plan = self._plan_tools(intent, request)

            # 3. Execute tools
            tool_results = await self._execute_tools(tool_plan, request)

            # 4. Load user preferences and filter tool results
            prefs = await self._load_prefs_for_user(db, request.user_id)
            tool_results = self._filter_tool_results_by_preferences(
                tool_results, intent, prefs
            )

            # 5. Synthesize answer with LLM + RAG (returns answer + cards)
            answer, llm_used, rag_sources, cards = await self._synthesize_answer(
                request.query, intent, tool_results, request.user_id
            )

            # 6. Build metrics
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            metrics = AgentMetrics(
                emails_scanned=self._count_emails_scanned(tool_results),
                tool_calls=len(tool_results),
                rag_sources=rag_sources,
                duration_ms=duration_ms,
                llm_used=llm_used,
            )

            # 7. Build response
            response = AgentRunResponse(
                user_id=request.user_id,
                query=request.query,
                mode=request.mode,
                context=request.context,
                status="done",
                answer=answer,
                cards=cards,
                tools_used=[tr.tool_name for tr in tool_results],
                metrics=metrics,
                completed_at=datetime.utcnow(),
                intent=intent,  # Add intent to response
            )

            # 8. Record telemetry
            record_agent_run(
                intent=intent,
                mode=request.mode,
                status="success",
                duration_ms=duration_ms,
            )

            return response

        except Exception as e:
            logger.error(f"Agent run failed: {e}", exc_info=True)
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Record failure
            record_agent_run(
                intent="unknown",
                mode=request.mode,
                status="error",
                duration_ms=duration_ms,
            )

            # Return error response
            return AgentRunResponse(
                user_id=request.user_id,
                query=request.query,
                mode=request.mode,
                context=request.context,
                status="error",
                answer="I encountered an error processing your request. Please try again.",
                cards=[
                    AgentCard(
                        kind="error",
                        title="System Error",
                        body=f"An error occurred: {str(e)}",
                        email_ids=[],
                        meta={"error_type": type(e).__name__},
                    )
                ],
                tools_used=[],
                metrics=AgentMetrics(duration_ms=duration_ms),
                completed_at=datetime.utcnow(),
                error_message=str(e),
            )

    async def _classify_intent(self, query: str) -> str:
        """
        DEPRECATED: Use classify_intent() function instead.

        Kept for backward compatibility during transition.
        """
        return classify_intent(query)

    def _plan_tools(
        self, intent: str, request: AgentRunRequest
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Plan which tools to execute based on intent.

        Intent-specific tool planning:
        - suspicious: email_search + security_scan
        - bills: email_search + applications_lookup
        - interviews: email_search + applications_lookup + thread_detail
        - followups: email_search + applications_lookup + thread_detail
        - profile: profile_stats + email_search
        - generic: email_search only

        Returns: List of (tool_name, params) tuples
        """
        plan = []
        time_window_days = request.context.time_window_days or 30

        # All intents start with email_search
        email_search_params = {
            "query_text": request.query,
            "time_window_days": time_window_days,
            "max_results": 50,
        }

        if intent == "suspicious":
            # suspicious: email_search + security_scan
            plan.append(("email_search", email_search_params))
            plan.append(
                (
                    "security_scan",
                    {
                        "email_ids": [],  # Will be populated from email_search
                        "force_rescan": False,
                    },
                )
            )

        elif intent == "bills":
            # bills: email_search + applications_lookup
            plan.append(("email_search", {**email_search_params, "max_results": 20}))
            # applications_lookup params will be populated after email_search
            plan.append(("applications_lookup", {"email_ids": [], "max_results": 50}))

        elif intent == "interviews":
            # interviews: email_search + applications_lookup + thread_detail
            plan.append(("email_search", {**email_search_params, "max_results": 20}))
            plan.append(("applications_lookup", {"email_ids": [], "max_results": 50}))
            plan.append(
                (
                    "thread_detail",
                    {"thread_id": None, "email_ids": [], "max_emails": 20},
                )
            )

        elif intent == "followups":
            # followups: email_search + applications_lookup + thread_detail
            plan.append(("email_search", {**email_search_params, "max_results": 20}))
            plan.append(("applications_lookup", {"email_ids": [], "max_results": 50}))
            plan.append(
                (
                    "thread_detail",
                    {"thread_id": None, "email_ids": [], "max_emails": 20},
                )
            )

        elif intent == "profile":
            # profile: profile_stats first, then email_search for context
            plan.append(
                (
                    "profile_stats",
                    {
                        "time_window_days": time_window_days,
                    },
                )
            )
            plan.append(("email_search", {**email_search_params, "max_results": 10}))

        else:  # generic
            # generic: just email_search
            plan.append(("email_search", {**email_search_params, "max_results": 20}))

        return plan

    async def _execute_tools(
        self, tool_plan: List[Tuple[str, Dict[str, Any]]], request: AgentRunRequest
    ) -> List[ToolResult]:
        """
        Execute tool plan with timeouts and fallbacks.

        Handles dynamic parameter population (e.g., email_ids from email_search).
        TODO: Add parallel execution for independent tools.
        """
        results = []
        email_ids_from_search = []

        for tool_name, params in tool_plan:
            try:
                start_time = datetime.utcnow()

                # Populate dynamic params from previous tool results
                if tool_name == "applications_lookup" and not params.get("email_ids"):
                    # Use email_ids from email_search
                    params["email_ids"] = email_ids_from_search[:50]  # Cap at 50

                if tool_name == "security_scan" and not params.get("email_ids"):
                    # Use email_ids from email_search
                    params["email_ids"] = email_ids_from_search[:50]  # Cap at 50

                if tool_name == "thread_detail":
                    # Use thread_id from first email in search results
                    if not params.get("thread_id") and email_ids_from_search:
                        # Extract thread_id from email_search results
                        for r in results:
                            if r.tool_name == "email_search" and r.status == "success":
                                emails = r.data.get("emails", [])
                                if emails:
                                    params["thread_id"] = emails[0].get("thread_id")
                                break

                # Execute tool with timeout
                result = await asyncio.wait_for(
                    self.tools.execute(tool_name, params, request.user_id), timeout=10.0
                )

                duration_ms = int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                )
                result.duration_ms = duration_ms

                results.append(result)

                # Collect email_ids for subsequent tools
                if tool_name == "email_search" and result.status == "success":
                    emails = result.data.get("emails", [])
                    email_ids_from_search = [e.get("id") for e in emails if e.get("id")]

                # Record success
                record_tool_call(tool_name, "success", duration_ms)

            except asyncio.TimeoutError:
                logger.warning(f"Tool {tool_name} timed out")
                results.append(
                    ToolResult(
                        tool_name=tool_name,
                        status="timeout",
                        summary=f"{tool_name} timed out",
                        error_message="Tool execution exceeded timeout",
                    )
                )
                record_tool_call(tool_name, "timeout", 10000)

            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)
                results.append(
                    ToolResult(
                        tool_name=tool_name,
                        status="error",
                        summary=f"{tool_name} failed",
                        error_message=str(e),
                    )
                )
                record_tool_call(tool_name, "error", 0)

        return results

    async def _synthesize_answer(
        self, query: str, intent: str, tool_results: List[ToolResult], user_id: str
    ) -> Tuple[str, Optional[str], int, List[AgentCard]]:
        """
        Synthesize final answer from tool results using LLM with RAG context.

        Retrieves relevant email and KB contexts to enhance LLM response.
        Returns structured JSON with answer + cards with citations.

        Returns: (answer, llm_used, rag_sources_count, cards)
        """
        try:
            # Retrieve RAG contexts
            rag_email_count = 0
            rag_kb_count = 0
            email_contexts = []
            kb_contexts = []

            try:
                if ES_ENABLED:
                    es = AsyncElasticsearch(ES_URL)

                    # Get email contexts (similar emails from user's inbox)
                    email_contexts = await retrieve_email_contexts(
                        es=es,
                        user_id=user_id,
                        query_text=query,
                        time_window_days=90,  # Last 90 days
                        max_results=5,
                    )
                    rag_email_count = len(email_contexts)

                    # Get KB contexts (general knowledge)
                    kb_contexts = await retrieve_kb_contexts(
                        es=es, query_text=query, max_results=3
                    )
                    rag_kb_count = len(kb_contexts)

                    # Close ES client
                    await es.close()

            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}", exc_info=True)

            # Use structured LLM answering with citations
            # Note: complete_agent_answer needs the full request object
            # We'll reconstruct it from available data
            from app.schemas_agent import AgentRunRequest, AgentContext

            request = AgentRunRequest(
                query=query,
                mode="preview_only",  # Default mode
                context=AgentContext(time_window_days=90),
                user_id=user_id,
            )

            answer, cards = await complete_agent_answer(
                request=request,
                intent=intent,
                tool_results=tool_results,
                email_contexts=email_contexts,
                kb_contexts=kb_contexts,
            )

            # Build deterministic cards from tool results for scan intents
            # This prevents the LLM from overriding our thread_list cards
            intent_spec = self._get_intent_spec(intent)
            if intent_spec:
                # Build metrics first (needed by card builder)
                metrics_dict = self._build_metrics_from_spec(
                    spec=intent_spec,
                    tool_results=tool_results,
                    time_window_days=request.context.time_window_days,
                )

                # Build deterministic cards (summary + thread_list)
                deterministic_card_objects = self._build_cards_from_spec(
                    spec=intent_spec,
                    tool_results=tool_results,
                    metrics=metrics_dict,
                    time_window_days=request.context.time_window_days,
                )

                # Convert AgentCard objects to dicts for merging
                tool_cards = [card.dict() for card in deterministic_card_objects]

                # Convert LLM cards to dicts (they're already AgentCard objects)
                llm_cards = [card.dict() for card in cards] if cards else None

                # Merge: tool cards always win, LLM cards only add extras
                merged_card_dicts = merge_cards_with_llm(
                    tool_cards=tool_cards,
                    llm_cards=llm_cards,
                )

                # Convert back to AgentCard objects
                cards = [AgentCard(**card_dict) for card_dict in merged_card_dicts]

            # Calculate total RAG sources
            total_rag_sources = rag_email_count + rag_kb_count

            # Log metrics
            logger.info(
                f"RAG: {rag_email_count} email contexts, {rag_kb_count} KB contexts, "
                f"{len(cards)} cards generated"
            )

            # Determine LLM used from cards metadata
            llm_used = "ollama"  # Default
            if cards and cards[0].meta.get("llm_used"):
                llm_used = cards[0].meta["llm_used"]
            elif cards and cards[0].meta.get("fallback"):
                llm_used = "fallback"

            return answer, llm_used, total_rag_sources, cards

        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}", exc_info=True)

            # Fallback: simple concatenation
            fallback_answer = " ".join(
                [tr.summary for tr in tool_results if tr.status == "success"]
            )
            fallback_cards = [
                AgentCard(
                    kind="error",
                    title="Answer generation failed",
                    body="I had trouble generating a structured answer.",
                    email_ids=[],
                    meta={"fallback": True, "error": str(e)},
                )
            ]
            return (
                fallback_answer or "I couldn't process your request.",
                "fallback",
                0,
                fallback_cards,
            )

    # DEPRECATED: Card building is now done by LLM in answering.py
    # def _build_cards(self, tool_results: List[ToolResult]) -> List[AgentCard]:
    #     """Build UI cards from tool results."""
    #     # This method is no longer used - cards are generated by the LLM
    #     # with citations in complete_agent_answer()
    #     pass

    def _build_metrics_from_spec(
        self, spec: IntentSpec, tool_results: List[ToolResult], time_window_days: int
    ) -> Dict[str, Any]:
        """
        Build metrics dict based on intent spec and tool results.

        Returns metrics with intent-specific fields:
        - suspicious: emails_scanned, matches, high_risk, time_window_days
        - followups: conversations_scanned, needs_reply, time_window_days
        - bills: total_bills, due_soon, overdue, other, time_window_days
        - etc.
        """
        metrics = {
            "time_window_days": time_window_days,
            "tool_calls": len(tool_results),
        }

        if spec.name == "suspicious":
            # Extract from security_scan tool result
            security_scan = next(
                (tr for tr in tool_results if tr.tool_name == "security_scan"),
                None,
            )
            if security_scan and security_scan.status == "success":
                data = security_scan.data or {}
                matches = data.get("matches", [])
                metrics.update(
                    {
                        "emails_scanned": data.get("emails_scanned", 0),
                        "matches": len(matches),
                        "high_risk": sum(
                            1 for m in matches if m.get("risk_level") == "high"
                        ),
                    }
                )
            else:
                metrics.update({"emails_scanned": 0, "matches": 0, "high_risk": 0})

        elif spec.name == "followups":
            # Extract from email_search tool result
            email_search = next(
                (tr for tr in tool_results if tr.tool_name == "email_search"),
                None,
            )
            if email_search and email_search.status == "success":
                data = email_search.data or {}
                threads = data.get("threads", [])
                unreplied = [t for t in threads if not t.get("replied", True)]
                metrics.update(
                    {
                        "conversations_scanned": len(threads),
                        "needs_reply": len(unreplied),
                    }
                )
            else:
                metrics.update({"conversations_scanned": 0, "needs_reply": 0})

        elif spec.name == "bills":
            # Extract from email_search + bill_parser
            email_search = next(
                (tr for tr in tool_results if tr.tool_name == "email_search"),
                None,
            )
            if email_search and email_search.status == "success":
                data = email_search.data or {}
                bills = data.get("bills", [])
                due_soon = [b for b in bills if b.get("status") == "due_soon"]
                overdue = [b for b in bills if b.get("status") == "overdue"]
                other = [
                    b for b in bills if b.get("status") not in ["due_soon", "overdue"]
                ]
                metrics.update(
                    {
                        "total_bills": len(bills),
                        "due_soon": len(due_soon),
                        "overdue": len(overdue),
                        "other": len(other),
                    }
                )
            else:
                metrics.update(
                    {"total_bills": 0, "due_soon": 0, "overdue": 0, "other": 0}
                )

        # Add more intent-specific metrics as needed

        return metrics

    def _get_intent_spec(self, intent_name: str) -> Optional[IntentSpec]:
        """Get IntentSpec for a given intent name."""
        return INTENT_SPECS.get(intent_name)

    def _build_thread_summary(
        self,
        thread_id: str,
        thread_emails: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build a ThreadSummary dict from a group of emails."""
        # Sort by received_at to get the latest
        sorted_emails = sorted(
            thread_emails,
            key=lambda e: e.get("received_at", ""),
            reverse=True,
        )
        latest = sorted_emails[0]

        # Build gmail URL
        gmail_url = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"

        return {
            "threadId": thread_id,
            "subject": latest.get("subject", ""),
            "from": latest.get("sender", "") or latest.get("from_address", ""),
            "to": "",
            "lastMessageAt": latest.get("received_at", ""),
            "unreadCount": 0,
            "riskScore": latest.get("risk_score", 0),
            "labels": latest.get("labels", []),
            "snippet": latest.get("snippet", ""),
            "gmailUrl": gmail_url,
        }

    def _group_emails_by_thread(
        self,
        emails: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group emails by thread_id."""
        thread_map = {}
        for email in emails:
            tid = email.get("thread_id") or email.get("id")
            if tid not in thread_map:
                thread_map[tid] = []
            thread_map[tid].append(email)
        return thread_map

    def _build_thread_cards(
        self,
        *,
        intent: str,
        title: str,
        summary_body_if_any: Optional[str],
        threads: List[Dict[str, Any]],
        time_window_days: int,
        preview_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Build both summary and thread_list cards using unified contract.

        Returns:
            - Summary card (followups_summary/generic_summary) with count
            - Thread list card (thread_list) only if threads is non-empty

        This guarantees:
        - No "multiple follow-ups" with count: 0
        - Thread viewer only appears when threads actually exist
        """
        count = len(threads)

        # Summary card - use intent-specific kind for backwards compatibility
        summary_kind = (
            "followups_summary" if intent == "followups" else "generic_summary"
        )

        summary_card: Dict[str, Any] = {
            "kind": summary_kind,
            "title": title,
            "time_window_days": time_window_days,
            "mode": "preview_only" if preview_only else "normal",
            "threads": [],  # Legacy field - keep empty
            "email_ids": [],
            "meta": {
                "count": count,
                "time_window_days": time_window_days,
            },
        }

        # Set body based on count
        if count == 0:
            summary_card["body"] = (
                "You're all caught up – I couldn't find anything matching this in the last "
                f"{time_window_days} days."
            )
        else:
            summary_card["body"] = summary_body_if_any or (
                f"I found {count} item{'s' if count != 1 else ''} for this scan "
                f"in the last {time_window_days} days."
            )

        cards: List[Dict[str, Any]] = [summary_card]

        # Thread list card - only when we have threads
        if count > 0:
            thread_list_card = {
                "kind": "thread_list",
                "intent": intent,
                "title": title,
                "time_window_days": time_window_days,
                "mode": "normal",
                "threads": threads[:10],  # Limit to 10 threads
                "email_ids": [],
                "body": "",
                "meta": {
                    "count": count,
                    "time_window_days": time_window_days,
                },
            }
            cards.append(thread_list_card)

        return cards

    def _build_cards_from_spec(
        self,
        spec: IntentSpec,
        tool_results: List[ToolResult],
        metrics: Dict[str, Any],
        time_window_days: int,
    ) -> List[AgentCard]:
        """
        Build card data structures with zero/non-zero handling per intent spec.

        Uses unified _build_thread_cards helper to ensure consistency:
        - Summary card always present
        - Thread list card only when threads exist
        """
        cards = []

        if spec.name == "suspicious":
            security_scan = next(
                (tr for tr in tool_results if tr.tool_name == "security_scan"),
                None,
            )

            # Build thread summaries from security_scan results
            thread_summaries = []
            if security_scan and security_scan.status == "success":
                data = security_scan.data or {}
                risky_emails = data.get("risky_emails", [])

                thread_map = self._group_emails_by_thread(risky_emails)
                for thread_id, thread_emails in thread_map.items():
                    thread_summaries.append(
                        self._build_thread_summary(thread_id, thread_emails)
                    )

            # Use unified card builder
            count = len(thread_summaries)
            title = spec.zero_title if count == 0 else spec.nonzero_title
            summary_body = (
                f"{count} suspicious email{'s' if count != 1 else ''} found "
                f"in the last {time_window_days} days."
                if count > 0
                else None
            )

            card_dicts = self._build_thread_cards(
                intent="suspicious",
                title=title,
                summary_body_if_any=summary_body,
                threads=thread_summaries,
                time_window_days=time_window_days,
                preview_only=True,
            )

            # Convert dicts to AgentCard objects
            for card_dict in card_dicts:
                cards.append(AgentCard(**card_dict))

        elif spec.name == "followups":
            email_search = next(
                (tr for tr in tool_results if tr.tool_name == "email_search"),
                None,
            )

            # Build thread summaries from email_search results
            thread_summaries = []
            if email_search and email_search.status == "success":
                data = email_search.data or {}
                emails = data.get("emails", [])

                thread_map = self._group_emails_by_thread(emails)
                for thread_id, thread_emails in thread_map.items():
                    thread_summaries.append(
                        self._build_thread_summary(thread_id, thread_emails)
                    )

            # Use unified card builder
            count = len(thread_summaries)
            title = spec.zero_title if count == 0 else spec.nonzero_title
            summary_body = (
                (
                    "You have multiple follow-ups awaiting your reply."
                    if count > 1
                    else "You have 1 follow-up awaiting your reply."
                )
                if count > 0
                else None
            )

            card_dicts = self._build_thread_cards(
                intent="followups",
                title=title,
                summary_body_if_any=summary_body,
                threads=thread_summaries,
                time_window_days=time_window_days,
                preview_only=True,
            )

            for card_dict in card_dicts:
                cards.append(AgentCard(**card_dict))

        elif spec.name == "interviews":
            email_search = next(
                (tr for tr in tool_results if tr.tool_name == "email_search"),
                None,
            )

            # Build thread summaries from email_search results
            thread_summaries = []
            if email_search and email_search.status == "success":
                data = email_search.data or {}
                emails = data.get("emails", [])

                thread_map = self._group_emails_by_thread(emails)
                for thread_id, thread_emails in thread_map.items():
                    thread_summaries.append(
                        self._build_thread_summary(thread_id, thread_emails)
                    )

            # Use unified card builder
            count = len(thread_summaries)
            title = spec.zero_title if count == 0 else spec.nonzero_title
            summary_body = (
                f"{count} interview-related email{'s' if count != 1 else ''} found "
                f"in the last {time_window_days} days."
                if count > 0
                else None
            )

            card_dicts = self._build_thread_cards(
                intent="interviews",
                title=title,
                summary_body_if_any=summary_body,
                threads=thread_summaries,
                time_window_days=time_window_days,
                preview_only=True,
            )

            for card_dict in card_dicts:
                cards.append(AgentCard(**card_dict))

        elif spec.name == "unsubscribe" or spec.name == "clean_promos":
            email_search = next(
                (tr for tr in tool_results if tr.tool_name == "email_search"),
                None,
            )

            # Build thread summaries from email_search results
            thread_summaries = []
            if email_search and email_search.status == "success":
                data = email_search.data or {}
                emails = data.get("emails", [])

                thread_map = self._group_emails_by_thread(emails)
                for thread_id, thread_emails in thread_map.items():
                    thread_summaries.append(
                        self._build_thread_summary(thread_id, thread_emails)
                    )

            # Use unified card builder
            count = len(thread_summaries)
            if spec.name == "unsubscribe":
                title = (
                    "Unsubscribe from Unopened Newsletters"
                    if count > 0
                    else "No Unopened Newsletters"
                )
                summary_body = (
                    f"{count} newsletters found that haven't been opened in {time_window_days} days."
                    if count > 0
                    else None
                )
            else:  # clean_promos
                title = spec.zero_title if count == 0 else spec.nonzero_title
                summary_body = (
                    f"{count} promotional email{'s' if count != 1 else ''} found "
                    f"in the last {time_window_days} days."
                    if count > 0
                    else None
                )

            card_dicts = self._build_thread_cards(
                intent=spec.name,
                title=title,
                summary_body_if_any=summary_body,
                threads=thread_summaries,
                time_window_days=time_window_days,
                preview_only=True,
            )

            for card_dict in card_dicts:
                cards.append(AgentCard(**card_dict))

        elif spec.name == "bills":
            email_search = next(
                (tr for tr in tool_results if tr.tool_name == "email_search"),
                None,
            )

            # Build thread summaries from email_search results
            thread_summaries = []
            if email_search and email_search.status == "success":
                data = email_search.data or {}
                emails = data.get("emails", [])

                thread_map = self._group_emails_by_thread(emails)
                for thread_id, thread_emails in thread_map.items():
                    thread_summaries.append(
                        self._build_thread_summary(thread_id, thread_emails)
                    )

            # Use unified card builder
            count = len(thread_summaries)
            title = spec.zero_title if count == 0 else spec.nonzero_title
            summary_body = (
                f"{count} bill{'s' if count != 1 else ''} found "
                f"in the last {time_window_days} days."
                if count > 0
                else None
            )

            card_dicts = self._build_thread_cards(
                intent="bills",
                title=title,
                summary_body_if_any=summary_body,
                threads=thread_summaries,
                time_window_days=time_window_days,
                preview_only=True,
            )

            for card_dict in card_dicts:
                cards.append(AgentCard(**card_dict))

        # Fallback for other intents
        else:
            # Generic summary card
            base_card = AgentCard(
                kind="generic_summary",
                title="Search Results",
                body="",
                email_ids=[],
                threads=[],
                meta={
                    "time_window_days": time_window_days,
                },
            )
            cards.append(base_card)

        return cards

    def _count_emails_scanned(self, tool_results: List[ToolResult]) -> int:
        """Count total emails scanned across all tools."""
        total = 0
        for result in tool_results:
            if result.tool_name == "email_search":
                total += len(result.data.get("emails", []))
        return total
