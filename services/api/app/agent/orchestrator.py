"""
Agent v2 - MailboxAgentOrchestrator

Coordinates:
1. Intent classification (rule-based + LLM fallback)
2. Tool planning (which tools to call, in what order)
3. Tool execution (with timeouts + fallbacks)
4. LLM synthesis (generate final answer from tool results)
"""

from typing import List, Dict, Any, Optional, Tuple
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
        1. Classify intent
        2. Plan tools
        3. Execute tools (parallel where possible)
        4. Synthesize answer with LLM + RAG
        5. Build cards from tool results
        6. Record metrics
        """
        start_time = datetime.utcnow()

        try:
            # 1. Classify intent
            intent = await self._classify_intent(request.query)
            logger.info(f"Agent run: query='{request.query}', intent='{intent}'")

            # 2. Plan tool execution
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
        Classify user intent from query.

        Phase 1: Simple keyword matching
        Phase 2: Add LLM classification for ambiguous queries

        Returns: "suspicious" | "bills" | "follow_ups" | "interviews" | "generic"
        """
        query_lower = query.lower()

        # Keyword-based classification (Phase 1)
        if any(
            kw in query_lower
            for kw in ["suspicious", "phishing", "spam", "scam", "risky", "dangerous"]
        ):
            return "suspicious"

        if any(kw in query_lower for kw in ["bill", "invoice", "payment", "due"]):
            return "bills"

        if any(
            kw in query_lower for kw in ["follow up", "reply", "respond", "waiting"]
        ):
            return "follow_ups"

        if any(
            kw in query_lower
            for kw in ["interview", "recruiter", "job", "application", "offer"]
        ):
            return "interviews"

        # TODO Phase 2: LLM-based classification for ambiguous queries
        return "generic"

    def _plan_tools(
        self, intent: str, request: AgentRunRequest
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Plan which tools to execute based on intent.

        Returns: List of (tool_name, params) tuples
        """
        plan = []

        # Intent-specific tool selection
        if intent == "suspicious":
            plan.append(
                (
                    "email_search",
                    {
                        "query_text": request.query,
                        "time_window_days": request.context.time_window_days,
                        # Don't filter by risk_min - let security_scan categorize
                        "max_results": 50,
                    },
                )
            )
            # Add security scan to categorize emails by risk
            plan.append(("security_scan", {"email_ids": []}))  # Populated after search

        elif intent == "bills":
            plan.append(
                (
                    "email_search",
                    {
                        "query_text": request.query,
                        "time_window_days": request.context.time_window_days,
                        "max_results": 20,
                    },
                )
            )

        elif intent == "follow_ups":
            plan.append(
                (
                    "email_search",
                    {
                        "query_text": request.query,
                        "time_window_days": request.context.time_window_days,
                        "max_results": 20,
                    },
                )
            )

        elif intent == "interviews":
            plan.append(
                (
                    "email_search",
                    {
                        "query_text": request.query,
                        "time_window_days": request.context.time_window_days,
                        "max_results": 20,
                    },
                )
            )
            plan.append(("applications_lookup", {"email_ids": []}))

        else:  # generic
            plan.append(
                (
                    "email_search",
                    {
                        "query_text": request.query,
                        "time_window_days": request.context.time_window_days,
                        "max_results": 20,
                    },
                )
            )

        return plan

    async def _execute_tools(
        self, tool_plan: List[Tuple[str, Dict[str, Any]]], request: AgentRunRequest
    ) -> List[ToolResult]:
        """
        Execute tool plan with timeouts and fallbacks.

        TODO Phase 1.2: Add parallel execution for independent tools
        """
        results = []

        for tool_name, params in tool_plan:
            try:
                start_time = datetime.utcnow()

                # Execute tool with timeout
                result = await asyncio.wait_for(
                    self.tools.execute(tool_name, params, request.user_id), timeout=10.0
                )

                duration_ms = int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                )
                result.duration_ms = duration_ms

                results.append(result)

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
