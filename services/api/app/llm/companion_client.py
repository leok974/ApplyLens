"""
Phase 3.1: LLM Client for ApplyLens Companion Extension

Supports OpenAI, Ollama, and template-based fallback for generating form answers.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Environment configuration
LLM_ENABLED = os.getenv("COMPANION_LLM_ENABLED", "0") == "1"
LLM_PROVIDER = os.getenv("COMPANION_LLM_PROVIDER", "openai")  # "openai" | "ollama"
LLM_MODEL = os.getenv("COMPANION_LLM_MODEL", "gpt-4o-mini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class CompanionLLMError(Exception):
    """Raised when LLM generation fails."""

    pass


def generate_form_answers_llm(
    fields: List[Dict[str, Any]],
    profile: Dict[str, Any],
    job_context: Optional[Dict[str, Any]] = None,
    style: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Generate form answers using LLM or template fallback.

    Args:
        fields: List of field descriptors with selector, semantic_key, label
        profile: User profile data (from /api/profile/me)
        job_context: Optional job posting details
        style: Optional generation style preferences

    Returns:
        Dict mapping semantic_key to generated answer text

    Raises:
        CompanionLLMError: If LLM call fails and fallback is disabled
    """
    if not LLM_ENABLED:
        logger.info("LLM disabled, using template fallback")
        return _generate_template_answers(fields, profile)

    try:
        prompt = _build_form_prompt(fields, profile, job_context, style)

        if LLM_PROVIDER == "openai":
            raw_response = _call_openai(prompt)
        elif LLM_PROVIDER == "ollama":
            raw_response = _call_ollama(prompt)
        else:
            raise CompanionLLMError(f"Unknown LLM provider: {LLM_PROVIDER}")

        answers = _parse_llm_output(raw_response, fields)
        logger.info(f"Generated {len(answers)} answers via {LLM_PROVIDER}")
        return answers

    except Exception as exc:
        logger.error(f"LLM generation failed: {exc}", exc_info=True)
        # Fallback to templates on error
        return _generate_template_answers(fields, profile)


def _build_form_prompt(
    fields: List[Dict[str, Any]],
    profile: Dict[str, Any],
    job_context: Optional[Dict[str, Any]],
    style: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build structured prompt for LLM.

    Returns a dict that will be converted to JSON for the LLM.
    """
    system_prompt = """You are an expert job application assistant. Generate ATS-friendly answers for application form fields.

CRITICAL RULES:
1. Never fabricate employment history or education
2. Never include URLs or links
3. Keep answers concise and relevant to the field
4. Use professional, error-free language
5. Match the tone indicated by the generation style
6. Only use information from the provided profile

For each field, return ONLY the answer text, no explanations."""

    field_descriptions = [
        {
            "semantic_key": f["semantic_key"],
            "label": f.get("label", f["semantic_key"]),
            "type": f.get("type", "text"),
        }
        for f in fields
    ]

    user_prompt = {
        "task": "Generate answers for these application form fields",
        "fields": field_descriptions,
        "profile": {
            "first_name": profile.get("first_name"),
            "last_name": profile.get("last_name"),
            "email": profile.get("email"),
            "phone": profile.get("phone"),
            "summary": profile.get("summary"),
            "skills": profile.get("skills", []),
            # Don't include full employment history to avoid hallucination
        },
        "job_context": job_context or {},
        "style": style or {"tone": "professional", "length": "concise"},
    }

    return {
        "system": system_prompt,
        "user": user_prompt,
    }


def _call_openai(prompt: Dict[str, Any]) -> str:
    """Call OpenAI API."""
    try:
        import openai

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise CompanionLLMError("OPENAI_API_KEY not set")

        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": json.dumps(prompt["user"])},
            ],
            temperature=0.7,
            max_tokens=1500,
        )

        return response.choices[0].message.content or ""

    except ImportError as exc:
        raise CompanionLLMError("openai package not installed") from exc
    except Exception as exc:
        raise CompanionLLMError(f"OpenAI call failed: {exc}") from exc


def _call_ollama(prompt: Dict[str, Any]) -> str:
    """Call Ollama API."""
    try:
        import requests

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": LLM_MODEL,
                "prompt": f"{prompt['system']}\n\n{json.dumps(prompt['user'])}",
                "stream": False,
            },
            timeout=30,
        )
        response.raise_for_status()

        return response.json().get("response", "")

    except ImportError as exc:
        raise CompanionLLMError("requests package not installed") from exc
    except Exception as exc:
        raise CompanionLLMError(f"Ollama call failed: {exc}") from exc


def _parse_llm_output(raw: str, fields: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Parse LLM response into semantic_key -> answer mapping.

    Expected format: JSON object with semantic keys or structured text.
    """
    # Try to extract JSON from response
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # Fallback: look for key-value pairs
    answers = {}
    for field in fields:
        key = field["semantic_key"]
        # Look for "key: value" pattern
        pattern = rf"{re.escape(key)}\s*:\s*(.+?)(?:\n|$)"
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            answers[key] = match.group(1).strip()

    return answers


def _generate_template_answers(
    fields: List[Dict[str, Any]],
    profile: Dict[str, Any],
) -> Dict[str, str]:
    """
    Simple template-based fallback when LLM is unavailable.
    """
    answers = {}

    for field in fields:
        key = field["semantic_key"]

        # Direct profile mapping
        if key in profile and profile[key]:
            answers[key] = str(profile[key])
            continue

        # Common field templates
        if key == "summary":
            answers[key] = profile.get(
                "summary", "Experienced professional seeking new opportunities."
            )
        elif key == "cover_letter":
            summary = profile.get("summary", "")
            answers[key] = (
                f"Dear Hiring Manager,\n\n"
                f"I am interested in this position. {summary}\n\n"
                f"Thank you for your consideration."
            )
        elif key in ("why_interested", "motivation"):
            answers[key] = (
                "I am excited about this opportunity and believe my skills align well with your needs."
            )
        else:
            # Generic fallback
            answers[key] = profile.get(key, "")

    return answers
