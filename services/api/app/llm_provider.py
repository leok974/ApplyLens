"""
LLM provider with fallback chain: Ollama (local) → OpenAI → Template

This module provides a unified interface for LLM text generation with:
- Primary: Local Ollama via infra-ollama-1 (llama3:latest)
- Fallback: OpenAI (gpt-4o-mini)
- Guaranteed: Deterministic template (never returns None)

IMPORTANT PRODUCTION NOTES:
- Model is llama3:latest (4.7GB, 2-4s response time)
- DO NOT switch back to gpt-oss:20b (too slow, >30s cold start)
- Ollama timeout is 30s to allow for model loading
- Hostname is infra-ollama-1:11434 (shared container on infra_net)

Safety:
- Low temperature (0.2) for grounded responses
- Short max_tokens (200) to prevent rambling
- Timeouts to avoid blocking
- No raw email bodies sent to models
"""

import os
import httpx
from typing import Optional

# Model configuration
# PRODUCTION: Uses infra-ollama-1 container with llama3:latest model
# DO NOT change to gpt-oss:20b - that model is too slow (>30s) for production
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://infra-ollama-1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


async def _call_ollama(prompt: str, timeout_s: float = 30.0) -> Optional[str]:
    """
    Call local Ollama. Return text or None if unavailable.

    Args:
        prompt: Text prompt for the model
        timeout_s: Timeout in seconds (default 30s for llama3:latest cold start)

    Returns:
        Generated text or None if failed

    Note: 30s timeout is required for llama3:latest model loading.
          DO NOT reduce to 8s - that will cause timeouts.
    """
    if not OLLAMA_BASE:
        return None

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(
                f"{OLLAMA_BASE}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 200,
                    },
                },
            )
        if resp.status_code != 200:
            return None
        data = resp.json()
        # Ollama returns {"response": "..."}
        text = data.get("response")
        if not text:
            return None
        return text.strip()
    except Exception as e:
        # Silent fail - ollama might be down, that's OK
        print(f"[llm_provider] Ollama unavailable: {e}")
        return None


async def _call_openai(prompt: str, timeout_s: float = 8.0) -> Optional[str]:
    """
    Fallback to OpenAI if local model fails.
    Uses chat-style completion with system prompt for grounding.

    Args:
        prompt: Text prompt for the model
        timeout_s: Timeout in seconds (default 8s)

    Returns:
        Generated text or None if failed
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
                        {
                            "role": "system",
                            "content": "You are ApplyLens Mailbox Assistant. Be concise, accurate, and grounded in provided data only.",
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    "temperature": 0.2,
                    "max_tokens": 200,
                },
            )
        if resp.status_code != 200:
            return None
        out = resp.json()
        choice = out.get("choices", [{}])[0]
        msg = choice.get("message", {}).get("content")
        if not msg:
            return None
        return msg.strip()
    except Exception as e:
        # Silent fail - OpenAI might be rate limited or key invalid
        print(f"[llm_provider] OpenAI unavailable: {e}")
        return None


async def llm_complete(prompt: str) -> tuple[str, str]:
    """
    Main entry point for LLM completions with guaranteed response.

    Tries providers in order:
    1. Ollama (local, fast, free)
    2. OpenAI (cloud, slower, costs money)
    3. Template (deterministic, always works)

    Args:
        prompt: Text prompt for the model

    Returns:
        Tuple of (generated_text, backend_name)
        backend_name is "ollama", "openai", or "template"

    This function NEVER returns None - it always has a fallback.
    """
    # 1. Try Ollama first
    txt = await _call_ollama(prompt)
    if txt:
        return txt, "ollama"

    # 2. Fallback to OpenAI
    txt = await _call_openai(prompt)
    if txt:
        return txt, "openai"

    # 3. Last resort deterministic template
    return (
        "I'm here to help interpret your mailbox results. Nothing urgent came up in the last window.",
        "template",
    )


async def generate_llm_text(prompt: str) -> Optional[str]:
    """
    High-level helper:
      1. Try Ollama local (fast, no cost)
      2. Fallback to OpenAI (slower, has cost)
      3. If neither works, return None (graceful degradation)

    Returns:
        Generated text or None if all providers failed
    """
    # Try local first
    txt = await _call_ollama(prompt)
    if txt:
        return txt

    # Fallback to OpenAI
    txt = await _call_openai(prompt)
    if txt:
        return txt

    # Both failed - caller should use deterministic fallback
    return None


async def generate_assistant_text(
    kind: str, prompt: str, fallback_template: str
) -> tuple[str, str]:
    """
    Phase 3 hybrid LLM helper with guaranteed response.

    Args:
        kind: Semantic label ("summary", "followup_prompt", "tone_regen", etc.)
        prompt: Instruction we'll pass to the model
        fallback_template: String to use if both providers fail

    Returns:
        Tuple of (generated_text, llm_used) where llm_used is "ollama", "openai", or "fallback"

    This ensures the assistant NEVER hangs or crashes due to LLM unavailability.
    """
    # Try Ollama first (fast, local, no cost)
    txt = await _call_ollama(prompt)
    if txt:
        print(f"[llm_provider] {kind} via Ollama")
        return (txt, "ollama")

    # Fallback to OpenAI (slower, has cost)
    txt = await _call_openai(prompt)
    if txt:
        print(f"[llm_provider] {kind} via OpenAI")
        return (txt, "openai")

    # Both failed - use safe template
    print(f"[llm_provider] {kind} via fallback template (both LLMs unavailable)")
    return (fallback_template, "fallback")
