"""
Intent Detection for Chat Assistant

Rule-based intent detection using regex patterns.
Can be enhanced with LLM-based classification later.
"""

import re
from typing import Literal

IntentType = Literal[
    "summarize", "find", "clean", "unsubscribe", 
    "flag", "follow-up", "calendar", "task"
]

# Intent patterns (order matters - more specific first)
INTENTS = {
    "unsubscribe": [
        r"\bunsubscribe\b",
        r"\bopt[- ]?out\b",
        r"\bstop (receiving|getting|emails)\b",
    ],
    "flag": [
        r"\b(suspicious|phish|scam|fraud|risk|risky)\b",
        r"\bflag\b",
        r"\b(new|unknown) domains?\b",
        r"\bhigh[- ]risk\b",
    ],
    "clean": [
        r"\bclean( up)?\b",
        r"\barchive\b",
        r"\bdeclutter\b",
        r"\bdelete\b",
        r"\bremove\b.*\b(old|promo|promotion)\b",
    ],
    "calendar": [
        r"\bcalendar\b",
        r"\breminders?\b",
        r"\bdue\b.*\b(date|before|by)\b",
        r"\bcreate.*\bevent\b",
        r"\bschedule\b",
    ],
    "task": [
        r"\btasks?\b",
        r"\btodo\b",
        r"\bassign\b",
        r"\bcreate.*\btask\b",
    ],
    "follow-up": [
        r"\bfollow[- ]?up\b",
        r"\bneeds?[- ]?reply\b",
        r"\bhavent?.*(replied|responded)\b",
        r"\bdraft.*\breply\b",
    ],
    "find": [
        r"\bfind\b",
        r"\bshow\b",
        r"\bsearch\b",
        r"\blook for\b",
        r"\blist\b",
        r"\bdisplay\b",
    ],
    "summarize": [
        r"\bsummariz",
        r"\boverview\b",
        r"\bwhat.*(came|arrived|received)\b",
        r"\btell me about\b",
        r"\brecent\b",
    ],
}


def detect_intent(text: str) -> IntentType:
    """
    Detect user intent from text using pattern matching.
    
    Args:
        text: User input text
        
    Returns:
        Detected intent (defaults to "summarize" if no match)
    """
    t = text.lower()
    
    # Check each intent's patterns
    for intent, patterns in INTENTS.items():
        if any(re.search(pattern, t) for pattern in patterns):
            return intent  # type: ignore
    
    # Fallback heuristics
    if "due" in t or "before" in t or "by" in t:
        return "calendar"
    
    if "?" in text and any(w in t for w in ["who", "what", "when", "where"]):
        return "find"
    
    # Default to summarize
    return "summarize"


def explain_intent(intent: IntentType) -> str:
    """
    Get a human-readable explanation of what the intent does.
    """
    explanations = {
        "summarize": "Summarize matching emails in a concise format",
        "find": "Find and list specific emails with reasons",
        "clean": "Propose archiving old promotional emails",
        "unsubscribe": "Propose unsubscribing from inactive newsletters",
        "flag": "Surface suspicious or high-risk emails with explanations",
        "follow-up": "Identify threads needing follow-up and suggest replies",
        "calendar": "Create calendar event reminders from email content",
        "task": "Create tasks from actionable email content",
    }
    return explanations.get(intent, "Process emails based on your request")


def explain_intent_tokens(text: str) -> list[str]:
    """
    Return a unique, human-readable list of regex tokens that matched the intent rules.
    Helps the UI surface 'due', 'before Friday', 'unless Best Buy', etc.
    """
    t = text.lower()
    hits = set()
    for intent, pats in INTENTS.items():
        for p in pats:
            m = re.search(p, t)
            if m:
                # take the literal text that matched if possible
                try:
                    hits.add(m.group(0))
                except Exception:
                    hits.add(p)
    # common phrases that users care about, even if not directly in INTENTS
    for phrase in [r"\bbefore\s+\w+\b", r"\bafter\s+\w+\b", r"\bunless\s+[^.]+", r"\bdue\b", r"\bnew domains?\b"]:
        m = re.search(phrase, t)
        if m:
            hits.add(m.group(0))
    return list(sorted(hits))


def extract_unless_brands(text: str) -> list[str]:
    """
    Extract brand/company phrases mentioned after 'unless'.
    Example: '... unless they're from Best Buy and Costco' -> ['best buy','costco']
    """
    t = text.lower()
    m = re.search(r"unless\s+(?:they['']re\s+from\s+|from\s+)?([^.]+)", t)
    if not m:
        return []
    chunk = m.group(1)
    # split by 'and', commas, semicolons
    parts = re.split(r"[,\;]|\band\b", chunk)
    brands = []
    for p in parts:
        s = p.strip()
        if not s:
            continue
        # remove generic words
        s = re.sub(r"\b(emails?|messages?|the|my|company|brand|newsletter[s]?)\b", "", s).strip()
        if s:
            brands.append(s)
    # de-dup
    seen, out = set(), []
    for b in brands:
        if b not in seen:
            out.append(b)
            seen.add(b)
    return out
