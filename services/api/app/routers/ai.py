"""
AI-powered features router.

Provides endpoints for:
- Email thread summarization with citations
- Natural language question answering
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.providers.ollama import ollama_chat, sanitize_user_text, check_ollama_health

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

# Feature flags
FEATURE_SUMMARIZE = os.getenv("FEATURE_SUMMARIZE", "1") == "1"


class SummarizeRequest(BaseModel):
    """Request to summarize an email thread."""

    thread_id: str = Field(..., description="Thread ID to summarize")
    max_citations: int = Field(
        default=3, ge=0, le=5, description="Maximum citations to return"
    )


class Citation(BaseModel):
    """Citation to a specific part of the thread."""

    snippet: str = Field(..., description="Quoted text snippet (<=160 chars)")
    message_id: str = Field(..., description="Source message ID")
    offset: Optional[int] = Field(None, description="Character offset in message")


class SummarizeResponse(BaseModel):
    """Response from summarization."""

    bullets: List[str] = Field(..., description="Summary bullets (max 5)")
    citations: List[Citation] = Field(
        default_factory=list, description="Supporting citations"
    )


async def get_thread_messages_mock(thread_id: str) -> List[Dict[str, Any]]:
    """
    Mock function to get thread messages.
    In production, this would query Gmail API or Elasticsearch.

    Args:
        thread_id: Thread identifier

    Returns:
        List of message dicts with from, text, id
    """
    # TODO: Replace with actual Gmail API or ES query
    # For now, return mock data
    if thread_id == "demo-1":
        return [
            {
                "id": "msg-1",
                "from_name": "Bianca Martinez",
                "from": "bianca@techcorp.com",
                "text": "Hi! Thanks for applying to TechCorp. We'd love to schedule an interview. Are you available Tuesday at 2pm or Wednesday at 10am?",
                "timestamp": "2025-10-15T09:00:00Z",
            },
            {
                "id": "msg-2",
                "from_name": "You",
                "from": "you@example.com",
                "text": "Hi Bianca, thanks for reaching out! Tuesday at 2pm works great for me. Should I prepare anything specific?",
                "timestamp": "2025-10-15T11:30:00Z",
            },
            {
                "id": "msg-3",
                "from_name": "Bianca Martinez",
                "from": "bianca@techcorp.com",
                "text": "Perfect! The interview will be 45 minutes with our CTO. Please review our product documentation and prepare to discuss your experience with React and TypeScript.",
                "timestamp": "2025-10-15T14:00:00Z",
            },
        ]

    return []


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_thread(request: SummarizeRequest):
    """
    Summarize an email thread using AI.

    Generates 5 concise bullets and extracts supporting citations.
    Uses Ollama for local-first inference.

    Args:
        request: Summarization request with thread_id

    Returns:
        Summary bullets and citations

    Raises:
        HTTPException: 404 if thread not found, 503 if Ollama unavailable, 504 if timeout
    """
    if not FEATURE_SUMMARIZE:
        raise HTTPException(status_code=503, detail="Summarization feature disabled")

    # Check Ollama health
    if not await check_ollama_health():
        logger.error("Ollama service unavailable")
        raise HTTPException(status_code=503, detail="AI service unavailable")

    # Get thread messages
    messages = await get_thread_messages_mock(request.thread_id)

    if not messages:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Build context from last N messages (cap tokens)
    max_messages = 12
    context_lines = []

    for msg in messages[-max_messages:]:
        who = msg.get("from_name") or msg.get("from", "Unknown")
        text = (msg.get("text") or msg.get("snippet") or "").strip()

        # Sanitize and truncate
        text = sanitize_user_text(text)[:1000]

        context_lines.append(f"{who}: {text}")

    context = "\n\n".join(context_lines)

    # Build prompt
    system_prompt = (
        "You are a precise email summarizer for hiring panels. Be concise and factual."
    )

    user_prompt = f"""Summarize this email conversation in exactly 5 concise bullets for a hiring panel.
Then extract up to {request.max_citations} direct supporting snippets (each <=160 characters).

Return ONLY valid JSON with this structure:
{{
  "bullets": ["bullet1", "bullet2", "bullet3", "bullet4", "bullet5"],
  "citations": [
    {{"snippet": "quoted text here", "message_id": "msg-X", "offset": 0}}
  ]
}}

Email conversation:
{context}
"""

    try:
        # Call Ollama
        response_text = await ollama_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,  # Lower temperature for factual summaries
            max_tokens=1500,
        )

        # Parse JSON response
        # Find JSON in response (may have markdown code blocks)
        response_text = response_text.strip()

        if "```json" in response_text:
            # Extract JSON from markdown code block
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        elif "```" in response_text:
            # Extract from generic code block
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        elif response_text.startswith("{"):
            json_str = response_text
        else:
            # Fallback: try to find JSON object
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
            else:
                logger.error(
                    f"Could not parse JSON from response: {response_text[:200]}"
                )
                raise ValueError("Invalid JSON response from AI")

        data = json.loads(json_str)

        # Validate and coerce
        bullets = data.get("bullets", [])
        citations_raw = data.get("citations", [])

        # Ensure exactly 5 bullets
        if len(bullets) < 5:
            bullets.extend(["[No additional details]"] * (5 - len(bullets)))
        bullets = bullets[:5]

        # Limit citations
        citations = []
        for cit in citations_raw[: request.max_citations]:
            citations.append(
                Citation(
                    snippet=cit.get("snippet", "")[:160],
                    message_id=cit.get("message_id", "unknown"),
                    offset=cit.get("offset"),
                )
            )

        return SummarizeResponse(bullets=bullets, citations=citations)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        raise HTTPException(status_code=500, detail="AI returned invalid format")

    except Exception as e:
        logger.error(f"Summarization failed: {e}")

        # Check if timeout
        if "timeout" in str(e).lower():
            raise HTTPException(status_code=504, detail="AI processing timeout")

        raise HTTPException(status_code=500, detail="Summarization failed")


@router.get("/health")
async def ai_health():
    """Check AI service health."""
    ollama_ok = await check_ollama_health()

    return {
        "ollama": "available" if ollama_ok else "unavailable",
        "features": {"summarize": FEATURE_SUMMARIZE},
    }
