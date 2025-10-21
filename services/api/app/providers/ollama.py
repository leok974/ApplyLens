"""
Ollama provider for local-first AI inference.

Provides chat completion interface using Ollama's OpenAI-compatible API.
Includes timeout handling, error management, and token usage tracking.
"""

import httpx
import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Configuration
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434")
# Fix for Windows: Replace localhost with 127.0.0.1 for httpx compatibility
if "localhost" in OLLAMA_BASE:
    OLLAMA_BASE = OLLAMA_BASE.replace("localhost", "127.0.0.1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
OLLAMA_TIMEOUT_MS = int(os.getenv("OLLAMA_TIMEOUT_MS", "120000"))
MAX_INPUT_CHARS = 50000  # Security limit


async def ollama_chat(
    messages: List[Dict[str, str]], 
    temperature: float = 0.7,
    max_tokens: int = 2000,
    **kwargs
) -> str:
    """
    Send chat completion request to Ollama.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        **kwargs: Additional parameters for Ollama
    
    Returns:
        Generated text content
    
    Raises:
        httpx.HTTPError: On API errors
        httpx.TimeoutException: On timeout
    """
    # Security: Validate and sanitize input
    for msg in messages:
        content = msg.get("content", "")
        if len(content) > MAX_INPUT_CHARS:
            raise ValueError(f"Message content exceeds {MAX_INPUT_CHARS} chars")
        
        # Basic sanitization (strip HTML tags if needed)
        # In production, use bleach or similar library
        if "<script" in content.lower() or "<iframe" in content.lower():
            logger.warning("Blocked potentially malicious HTML in message")
            raise ValueError("HTML tags not allowed in messages")
    
    # Build request payload
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
        **kwargs
    }
    
    timeout_seconds = OLLAMA_TIMEOUT_MS / 1000
    
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            logger.info(f"Calling Ollama: model={OLLAMA_MODEL}, messages={len(messages)}")
            
            response = await client.post(
                f"{OLLAMA_BASE}/v1/chat/completions",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract content
            content = data["choices"][0]["message"]["content"]
            
            # Log usage
            usage = data.get("usage", {})
            logger.info(
                f"Ollama response: "
                f"prompt_tokens={usage.get('prompt_tokens', 0)}, "
                f"completion_tokens={usage.get('completion_tokens', 0)}, "
                f"chars={len(content)}"
            )
            
            return content
            
    except httpx.TimeoutException as e:
        logger.error(f"Ollama timeout after {timeout_seconds}s")
        raise
    except httpx.HTTPError as e:
        logger.error(f"Ollama HTTP error: {e}")
        raise
    except Exception as e:
        logger.error(f"Ollama unexpected error: {e}")
        raise


async def check_ollama_health() -> bool:
    """
    Check if Ollama service is available.
    
    Returns:
        True if Ollama is reachable, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE}/api/tags")
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        return False


def sanitize_user_text(text: str) -> str:
    """
    Sanitize user input for AI prompts.
    
    Args:
        text: Raw user input
    
    Returns:
        Sanitized text safe for AI prompts
    """
    # Remove potentially malicious content
    sanitized = text.strip()
    
    # Block common injection patterns
    dangerous_patterns = [
        "ignore previous instructions",
        "disregard all",
        "system:",
        "<script",
        "<iframe",
        "javascript:",
        "data:text/html"
    ]
    
    for pattern in dangerous_patterns:
        if pattern.lower() in sanitized.lower():
            logger.warning(f"Blocked dangerous pattern in user text: {pattern}")
            sanitized = sanitized.replace(pattern, "[FILTERED]")
    
    # Truncate to reasonable length
    if len(sanitized) > MAX_INPUT_CHARS:
        sanitized = sanitized[:MAX_INPUT_CHARS] + "... [truncated]"
    
    return sanitized
