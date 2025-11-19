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
from app.agent.answering import complete_agent_answer
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
    "generic",
]

# Shared style guidelines for all intent prompts
SHARED_STYLE_HINT = (
    "\nGeneral style rules for all answers:\n"
    "- Explicitly mention: (a) how many emails were scanned, and (b) what time window you looked at "
    "if that information is available from the tools.\n"
    "- Always keep your answer under ~180 words.\n"
    "- Prefer short paragraphs and bullet lists over long text.\n"
    "- If nothing relevant was found, say so clearly and briefly, and suggest how the user might refine the query.\n"
)

# Intent-specific system prompts for LLM synthesis
INTENT_SYSTEM_PROMPTS: Dict[str, str] = {
    "suspicious": (
        "You are ApplyLens's email security assistant.\n"
        "The user is looking for potentially risky or scam emails in their job-search inbox.\n"
        "\n"
        "Write responses that are:\n"
        "- Short (1–2 short paragraphs max) plus a compact bullet list.\n"
        "- Concrete and grounded in the tool data (domains, subjects, links, risk scores).\n"
        "- Actionable: tell the user exactly what to do next (ignore, delete, report, or reply carefully).\n"
        "\n"
        "When you describe risky emails, always explain WHY they are risky using 2–4 bullet points per cluster "
        "(sender domain, payment requests, urgency, mismatched URLs, no company details). "
        "If no suspicious emails are found, say that clearly and briefly.\n"
        "\n"
        "Format your answer as:\n"
        "1. One short paragraph summarizing how many emails you scanned and whether anything looks risky.\n"
        "2. A bullet list called 'Key red flags' if you found suspicious emails.\n"
        "3. A bullet list called 'Safe next steps' telling the user what to do.\n"
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
        "If you do not find any bills or invoices, say that plainly and suggest how the user could refine the query.\n"
        "\n"
        "Format your answer as:\n"
        "1. One short paragraph summarizing how many bills/invoices you found and the overall situation.\n"
        "2. A bullet list with headings like 'Due soon', 'Overdue', and 'Other', listing only the most important items.\n"
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
        "If you find no interview-related emails, say that clearly and suggest whether the user should widen the date range.\n"
        "\n"
        "Format your answer as:\n"
        "1. One short paragraph summarizing interview/recruiter activity in the chosen time window.\n"
        "2. Three short bullet sections labelled 'Upcoming interviews', 'Waiting on recruiter', and 'Closed / done'.\n"
        "3. Under each section, list at most 3 items with company, role, and what to do next.\n"
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
        "If there is nothing to follow up on, say that explicitly and recommend what timeframe to watch next.\n"
        "\n"
        "Format your answer as:\n"
        "1. One short paragraph explaining how many threads might benefit from a follow-up.\n"
        "2. A numbered list of the top 3–5 follow-ups, each with company, role, last contact date, and a suggested follow-up angle.\n"
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
        "Format your answer as:\n"
        "1. One short paragraph summarizing overall volume and pace (total vs recent window).\n"
        "2. 3–5 bullet points for key stats (applications, recruiter replies, interviews, any non-trivial security risk).\n"
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
        "If the tools show no relevant emails, admit that clearly and suggest how the user could refine their query.\n"
        "\n"
        "Format your answer as:\n"
        "1. One paragraph summarizing what you found in the inbox that matches the query.\n"
        "2. A bullet list of 3–5 concrete next actions the user should take.\n"
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

    user_instructions = (
        f"User query:\n{query}\n\n"
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

    async def run(self, request: AgentRunRequest) -> AgentRunResponse:
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
            # 1. Classify intent using deterministic classifier
            intent = classify_intent(request.query)
            logger.info(f"Agent run: query='{request.query}', intent='{intent}'")

            # 2. Plan tool execution based on intent
            tool_plan = self._plan_tools(intent, request)

            # 3. Execute tools
            tool_results = await self._execute_tools(tool_plan, request)

            # 4. Synthesize answer with LLM + RAG (returns answer + cards)
            answer, llm_used, rag_sources, cards = await self._synthesize_answer(
                request.query, intent, tool_results, request.user_id
            )

            # 5. Build metrics
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            metrics = AgentMetrics(
                emails_scanned=self._count_emails_scanned(tool_results),
                tool_calls=len(tool_results),
                rag_sources=rag_sources,
                duration_ms=duration_ms,
                llm_used=llm_used,
            )

            # 6. Build response
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

            # 7. Record telemetry
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
                        "time_window_days": time_window_days,
                        "limit": 50,
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

    def _count_emails_scanned(self, tool_results: List[ToolResult]) -> int:
        """Count total emails scanned across all tools."""
        total = 0
        for result in tool_results:
            if result.tool_name == "email_search":
                total += len(result.data.get("emails", []))
        return total
