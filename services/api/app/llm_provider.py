"""
LLM provider with fallback chain: Ollama (local) → OpenAI → None

This module provides a unified interface for LLM text generation with:
- Primary: Local Ollama (OSS 20B model)
- Fallback: OpenAI (gpt-4o-mini or similar)
- Graceful degradation: Returns None if both fail

Safety:
- Low temperature (0.2) for grounded responses
- Short max_tokens (200) to prevent rambling
- Timeouts (8s) to avoid blocking
- No raw email bodies sent to models
"""

import os
import httpx
from typing import Optional

# Model configuration
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "oss-20b")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


async def _call_ollama(prompt: str) -> Optional[str]:
    """
    Call local Ollama. Return text or None if unavailable.
    Assumes Ollama's /api/generate endpoint style:
    POST { "model": "...", "prompt": "...", "stream": false }
    """
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                f"{OLLAMA_BASE}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
        if resp.status_code != 200:
            return None
        data = resp.json()
        # Most ollama builds return {"response": "..."}
        text = data.get("response")
        if not text:
            return None
        return text.strip()
    except Exception as e:
        # Silent fail - ollama might be down, that's OK
        print(f"[llm_provider] Ollama unavailable: {e}")
        return None


async def _call_openai(prompt: str) -> Optional[str]:
    """
    Fallback to OpenAI if local model fails.
    Uses chat-style completion with system prompt for grounding.
    """
    if not OPENAI_API_KEY:
        return None

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
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
