"""
Agent v2 - LLM Answering Module

Generates structured JSON responses with:
- Natural language answer
- UI cards with citations (email_ids)
- Metadata for rendering
"""

import json
import logging
import os
import httpx
from textwrap import dedent
from typing import Any, Dict, List, Tuple, Optional

from app.schemas_agent import (
    AgentRunRequest,
    AgentLLMAnswer,
    AgentCard,
    ToolResult,
    RAGContext,
)

logger = logging.getLogger(__name__)

# LLM configuration
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://infra-ollama-1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Intents that use deterministic card building
SCAN_INTENTS = {
    "followups",
    "unsubscribe",
    "suspicious",
    "bills",
    "clean_promos",
    "interviews",
}


def merge_cards_with_llm(
    *,
    tool_cards: List[Dict[str, Any]],
    llm_cards: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Combine deterministic tool cards with any extra LLM cards.

    Rules:
    - Tool cards always win for `thread_list` and summary cards.
    - LLM cards are only allowed to add *extra* non-conflicting cards
      (e.g. tips, tiny summaries) if they exist.

    This prevents the LLM from overriding our carefully constructed
    thread_list cards with single summary cards.
    """
    if not llm_cards:
        return tool_cards

    # Index tool cards by (kind, intent) so we don't duplicate
    existing_keys = set()
    for c in tool_cards:
        key = (c.get("kind"), c.get("intent"))
        existing_keys.add(key)

    merged: List[Dict[str, Any]] = list(tool_cards)

    for c in llm_cards:
        key = (c.get("kind"), c.get("intent"))

        # Never allow LLM to override thread_list or summary cards
        if key in existing_keys:
            continue

        # Allow extra small helper cards if you ever want that
        merged.append(c)

    return merged


def _summarize_tool_results(tool_results: List[ToolResult]) -> str:
    """Compact machine-readable summary of tools for the LLM."""
    parts = []
    for tr in tool_results:
        if tr.status != "success":
            parts.append(
                f"- {tr.tool_name}: ERROR ({tr.error_message or 'no message'})"
            )
            continue

        # keep this short – we just need counts and high-level info
        summary = tr.summary or ""
        parts.append(f"- {tr.tool_name}: {summary}")

    return "\n".join(parts) or "(no tools were run)"


def _summarize_rag_contexts(contexts: List[RAGContext]) -> str:
    """Turn RAG contexts into a short list for the model."""
    lines = []
    for ctx in contexts:
        # Prefix email IDs so the model can refer to them explicitly
        prefix = f"[email_id={ctx.source_id}]" if ctx.source_type == "email" else "[kb]"
        # Use content directly (RAGContext has source_type, source_id, content, score, metadata)
        content_preview = ctx.content.replace("\n", " ").strip()[:200]
        lines.append(f"{prefix} {content_preview}\n")
    return "\n".join(lines) or "(no additional context available)"


async def _call_ollama_json(
    system_prompt: str, user_prompt: str, timeout_s: float = 30.0
) -> Optional[dict]:
    """
    Call Ollama with JSON response format.

    Returns parsed JSON dict or None if unavailable.
    """
    if not OLLAMA_BASE:
        return None

    try:
        # Combine system + user into single prompt for Ollama
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(
                f"{OLLAMA_BASE}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": full_prompt,
                    "stream": False,
                    "format": "json",  # Request JSON format
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 500,  # Need more tokens for structured output
                    },
                },
            )

        if resp.status_code != 200:
            logger.warning(f"Ollama returned status {resp.status_code}")
            return None

        data = resp.json()
        text = data.get("response", "").strip()

        if not text:
            return None

        # Parse JSON
        # Strip code fences if present
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()

        return json.loads(text)

    except json.JSONDecodeError as e:
        logger.warning(f"Ollama returned invalid JSON: {e}")
        return None
    except Exception as e:
        logger.debug(f"Ollama unavailable: {e}")
        return None


async def _call_openai_json(
    system_prompt: str, user_prompt: str, timeout_s: float = 15.0
) -> Optional[dict]:
    """
    Call OpenAI with JSON response format.

    Returns parsed JSON dict or None if unavailable.
    """
    if not OPENAI_API_KEY:
        return None

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 800,  # Need more for structured output
                    "response_format": {"type": "json_object"},  # Enforce JSON
                },
            )

        if resp.status_code != 200:
            logger.warning(f"OpenAI returned status {resp.status_code}")
            return None

        out = resp.json()
        choice = out.get("choices", [{}])[0]
        msg = choice.get("message", {}).get("content")

        if not msg:
            return None

        # Parse JSON
        text = msg.strip()

        # Strip code fences if present
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()

        return json.loads(text)

    except json.JSONDecodeError as e:
        logger.warning(f"OpenAI returned invalid JSON: {e}")
        return None
    except Exception as e:
        logger.debug(f"OpenAI unavailable: {e}")
        return None


async def complete_agent_answer(
    *,
    request: AgentRunRequest,
    intent: str,
    tool_results: List[ToolResult],
    email_contexts: List[RAGContext],
    kb_contexts: List[RAGContext],
) -> Tuple[str, List[AgentCard]]:
    """
    Ask the LLM to synthesize a natural-language answer and card definitions
    from the tools + RAG contexts.

    Returns (answer, cards).
    """
    tools_block = _summarize_tool_results(tool_results)
    emails_block = _summarize_rag_contexts(email_contexts)
    kb_block = _summarize_rag_contexts(kb_contexts)

    # Build card generation instructions based on intent
    if intent in SCAN_INTENTS:
        card_instructions = dedent(
            """
            IMPORTANT: Do NOT create or modify UI cards for this intent.
            Cards are already built deterministically from tool results.
            Only provide natural-language text in the "answer" field.
            Set "cards" to an empty array: "cards": []
            """
        ).strip()
    else:
        card_instructions = dedent(
            """
            You MUST respond with **valid JSON** matching this schema:

            {
              "answer": "one-paragraph natural language answer for the user",
              "cards": [
                {
                  "kind": "suspicious_summary | bills_summary | followups_summary | interviews_summary | generic_summary | error",
                  "title": "short title for the UI card",
                  "body": "short summary body (do not just copy `answer`)",
                  "email_ids": ["id1", "id2"],
                  "meta": { "count": 3, "time_window_days": 7, "mode": "preview_only" }
                }
              ]
            }

            Rules:
            - Use email_ids only from the email contexts we provide (where you see [email_id=...]).
            - If there are no matching emails, clearly say that in both `answer` and the card.
            - Do not invent email IDs.
            - Do not repeat the same sentence in both `answer` and card `body`;
              the card should be a compact summary or status line.
            - If tools or context show an error, produce one `error` card and explain briefly.
            - Use intent-appropriate card kind: {intent}_summary for most cases.
            """
        ).strip()

    system_prompt = dedent(
        f"""
        You are the Mailbox Assistant inside ApplyLens, an email-focused assistant.

        INTENT: {intent}

        Intent-specific guidelines:
        - suspicious: Keep answer short (1-2 paragraphs + bullets). Explain WHY emails are risky (domains, urgency, payments). Be actionable.
        - bills: Focus on due dates, amounts, senders. Group into "due soon", "overdue", "other". Be concise.
        - interviews: Organize into sections: "Upcoming", "Waiting on recruiter", "Closed". Include company, role, dates, next actions.
        - followups: Prioritize top 3-5 follow-ups. Include company, role, last email date, suggested angle.
        - profile: Quantitative overview. Mention total emails, recent window, label/risk breakdowns. High-level trends only.
        - generic: Short and practical. 1 paragraph + bullet list of suggested actions.

        Always:
        - Base your reasoning ONLY on the tools and context provided.
        - Prefer conservative, security-aware answers.
        - If you are not sure about legitimacy of an email, say so and explain why.
        - Avoid repeating the exact same sentence multiple times.
        - Keep answers concise and practical.
        - Do NOT restate tool data exhaustively; summarize and prioritize.
        - Respond with ONLY the JSON object, no additional text.

        {card_instructions}
        """
    ).strip()

    user_prompt = dedent(
        f"""
        USER QUERY:
        {request.query}

        INTENT:
        {intent}

        MODE:
        {request.mode}

        TOOL RESULTS:
        {tools_block}

        EMAIL CONTEXTS:
        {emails_block}

        KNOWLEDGE CONTEXTS:
        {kb_block}

        Now produce the JSON response.
        """
    ).strip()

    # Try Ollama first
    logger.info("Requesting structured answer from LLM")
    data = await _call_ollama_json(system_prompt, user_prompt)
    llm_used = "ollama"

    # Fallback to OpenAI
    if not data:
        logger.info("Ollama failed, trying OpenAI")
        data = await _call_openai_json(system_prompt, user_prompt)
        llm_used = "openai"

    # If both failed, use fallback
    if not data:
        logger.warning("Both LLMs failed to generate structured answer, using fallback")
        fallback_answer = (
            "I looked at your mailbox using the available tools, but I couldn't "
            "generate a full structured answer due to an internal error. "
            "Here is a brief summary of what I saw:\n\n"
            f"{tools_block}"
        )
        error_card = AgentCard(
            kind="error",
            title="Mailbox Assistant error",
            body="I had trouble generating a structured answer. Please try again later.",
            email_ids=[],
            meta={"reason": "LLM unavailable", "fallback": True},
        )
        return fallback_answer, [error_card]

    # Parse and validate response
    try:
        parsed = AgentLLMAnswer.parse_obj(data)
        logger.info(
            f"LLM answer generated via {llm_used}: "
            f"{len(parsed.answer)} chars, {len(parsed.cards)} cards"
        )
        return parsed.answer, parsed.cards

    except Exception as exc:
        logger.exception(f"Failed to parse LLM response: {exc}")
        logger.debug(f"Raw LLM response: {data}")

        # Fallback with error details
        fallback_answer = (
            "I looked at your mailbox using the available tools, but I couldn't "
            "generate a full structured answer due to a parsing error. "
            "Here is a brief summary of what I saw:\n\n"
            f"{tools_block}"
        )
        error_card = AgentCard(
            kind="error",
            title="Mailbox Assistant error",
            body="I had trouble generating a structured answer. Please try again later.",
            email_ids=[],
            meta={"reason": str(exc), "llm_used": llm_used},
        )
        return fallback_answer, [error_card]
