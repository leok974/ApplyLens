"""
Token-safe text summarization utilities.

Prevents long email threads from exceeding LLM context limits.
"""

from typing import Any, Dict, List

# ~4k tokens rough estimate (3 chars per token average)
MAX_CHARS = 12000


def trim_for_llm(texts: List[str], max_chars: int = MAX_CHARS) -> List[str]:
    """
    Trim a list of texts to fit within LLM context limits.

    Args:
        texts: List of text strings (email bodies, snippets, etc.)
        max_chars: Maximum total characters (default ~4k tokens)

    Returns:
        Trimmed list of texts that fits within limit
    """
    out: List[str] = []
    total = 0

    for text in texts:
        # Cap each individual email to prevent single massive email
        text = text[:2000]

        # Stop if we'd exceed the limit
        if total + len(text) > max_chars:
            break

        out.append(text)
        total += len(text)

    return out


def extract_snippets_for_llm(
    docs: List[Dict[str, Any]], max_chars: int = MAX_CHARS
) -> List[str]:
    """
    Extract snippets from email documents for LLM processing.

    Prioritizes: snippet > body_text > subject

    Args:
        docs: List of email documents with text fields
        max_chars: Maximum total characters (default ~4k tokens)

    Returns:
        List of text snippets safe for LLM context
    """
    texts = []
    for doc in docs:
        # Try snippet first, then body, then subject as fallback
        text = doc.get("snippet") or doc.get("body_text") or doc.get("subject") or ""
        if text:
            texts.append(text)

    return trim_for_llm(texts, max_chars)
