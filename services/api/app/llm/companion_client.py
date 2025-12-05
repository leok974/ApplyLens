"""
Phase 3.1: LLM Client for ApplyLens Companion Extension

Supports OpenAI, Ollama, and template-based fallback for generating form answers.
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Import metrics
try:
    from app.metrics import (
        llm_generation_duration,
        llm_generation_requests,
        llm_template_fallbacks,
    )

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.warning("Metrics not available for LLM client")

# Environment configuration
LLM_ENABLED = os.getenv("COMPANION_LLM_ENABLED", "0") == "1"
LLM_PROVIDER = os.getenv("COMPANION_LLM_PROVIDER", "openai")  # "openai" | "ollama"
LLM_MODEL = os.getenv("COMPANION_LLM_MODEL", "gpt-4o-mini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
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
    profile_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Generate form answers using LLM or template fallback.

    Args:
        fields: List of field descriptors with selector, semantic_key, label
        profile: User profile data (legacy, kept for backward compatibility)
        job_context: Optional job posting details
        style: Optional generation style preferences
        profile_context: Structured profile context (name, experience, skills, etc.)

    Returns:
        Dict mapping semantic_key to generated answer text

    Raises:
        CompanionLLMError: If LLM call fails and fallback is disabled
    """
    start_time = time.time()
    provider = LLM_PROVIDER.lower()
    model = LLM_MODEL
    status = "success"
    result = {}

    try:
        if not LLM_ENABLED:
            logger.info("LLM disabled, using template fallback")
            if METRICS_AVAILABLE:
                llm_template_fallbacks.labels(reason="llm_disabled").inc()
            result = _generate_template_answers(fields, profile)
            status = "template_fallback"
            return result

        prompt = _build_form_prompt(
            fields, profile, job_context, style, profile_context
        )

        if LLM_PROVIDER == "openai":
            raw_response = _call_openai(prompt)
        elif LLM_PROVIDER == "ollama":
            raw_response = _call_ollama(prompt)
        else:
            logger.warning(f"Unknown LLM provider: {LLM_PROVIDER}")
            if METRICS_AVAILABLE:
                llm_template_fallbacks.labels(reason="unknown_provider").inc()
            result = _generate_template_answers(fields, profile)
            status = "template_fallback"
            return result

        answers = _parse_llm_output(raw_response, fields)
        logger.info(f"Generated {len(answers)} answers via {LLM_PROVIDER}")
        return answers

    except Exception as exc:
        logger.error(f"LLM generation failed: {exc}", exc_info=True)
        status = "error"
        if METRICS_AVAILABLE:
            llm_template_fallbacks.labels(reason="llm_error").inc()
        # Fallback to templates on error
        result = _generate_template_answers(fields, profile)
        return result

    finally:
        # Record metrics
        duration = time.time() - start_time
        if METRICS_AVAILABLE:
            llm_generation_requests.labels(
                provider=provider, model=model, status=status
            ).inc()
            llm_generation_duration.labels(provider=provider, model=model).observe(
                duration
            )


def _build_form_prompt(
    fields: List[Dict[str, Any]],
    profile: Dict[str, Any],
    job_context: Optional[Dict[str, Any]],
    style: Optional[Dict[str, Any]],
    profile_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build structured prompt for LLM with enhanced profile context.

    Args:
        fields: List of form fields to generate answers for
        profile: Legacy profile dict (kept for backward compatibility)
        job_context: Job posting details
        style: Generation style preferences
        profile_context: New structured profile context with experience, skills, etc.

    Returns a dict that will be converted to JSON for the LLM.
    """
    # Build profile summary lines for the system prompt
    profile_lines = []
    if profile_context:
        if profile_context.get("name"):
            profile_lines.append(f"Name: {profile_context['name']}")
        if profile_context.get("headline"):
            profile_lines.append(f"Headline: {profile_context['headline']}")
        if profile_context.get("experience_years") is not None:
            years = profile_context["experience_years"]
            profile_lines.append(f"Years of experience: {years}")
        if profile_context.get("target_roles"):
            roles = ", ".join(profile_context["target_roles"])
            profile_lines.append(f"Target roles: {roles}")
        if profile_context.get("tech_stack"):
            stack = ", ".join(profile_context["tech_stack"])
            profile_lines.append(f"Tech stack: {stack}")
        if profile_context.get("domains"):
            domains = ", ".join(profile_context["domains"])
            profile_lines.append(f"Preferred domains: {domains}")
        if profile_context.get("work_setup"):
            profile_lines.append(
                f"Work setup preference: {profile_context['work_setup']}"
            )
        if profile_context.get("locations"):
            locations = ", ".join(profile_context["locations"])
            profile_lines.append(f"Locations: {locations}")
        if profile_context.get("note"):
            profile_lines.append(f"Additional note: {profile_context['note']}")

    profile_summary = "\n".join(profile_lines) if profile_lines else "(no profile data)"

    # Build style instructions based on user preferences
    style_instructions = []
    if style:
        tone = style.get("tone", "confident")
        length = style.get("length", "medium")

        # Tone instructions
        tone_map = {
            "concise": "Use a concise, direct tone. Be brief and to-the-point.",
            "confident": "Use a confident, assertive tone. Be clear and self-assured.",
            "friendly": "Use a friendly, warm tone. Be approachable and personable.",
            "detailed": "Use a detailed, explanatory tone. Provide thorough responses.",
        }
        if tone in tone_map:
            style_instructions.append(tone_map[tone])

        # Length instructions
        length_map = {
            "short": "Keep answers SHORT (1-3 sentences maximum).",
            "medium": "Keep answers MEDIUM length (1-2 short paragraphs).",
            "long": "Provide LONGER answers (2-4 paragraphs with detail).",
        }
        if length in length_map:
            style_instructions.append(length_map[length])

    style_guidance = (
        "\n".join(style_instructions)
        if style_instructions
        else "Keep answers concise and relevant."
    )

    system_prompt = f"""You are ApplyLens Companion. You help the user fill job application forms.

Use the job context and profile summary to generate high-quality answers.

CRITICAL SAFETY RULES:
1. Never output email addresses, phone numbers, or direct URLs to personal profiles
2. Never fabricate employment history or education
3. If the profile indicates years of experience or preferred work setup, you MUST respect it
4. Use professional, error-free language
5. Answer in the same language as each question

STYLE GUIDANCE:
{style_guidance}

PROFILE SUMMARY:
{profile_summary}

Return ONLY a JSON object mapping field semantic_keys to answer text. No explanations."""

    field_descriptions = [
        {
            "semantic_key": f["semantic_key"],
            "label": f.get("label", f["semantic_key"]),
            "type": f.get("type", "text"),
        }
        for f in fields
    ]

    # Build job context description
    job_lines = []
    if job_context:
        if job_context.get("title"):
            job_lines.append(f"Title: {job_context['title']}")
        if job_context.get("company"):
            job_lines.append(f"Company: {job_context['company']}")
        if job_context.get("url"):
            job_lines.append(f"URL: {job_context['url']}")

    job_description = "\n".join(job_lines) if job_lines else "(no job context)"

    user_prompt = f"""JOB CONTEXT:
{job_description}

FIELDS TO ANSWER:
{json.dumps(field_descriptions, indent=2)}

Generate answers as a JSON object: {{"semantic_key": "answer text", ...}}"""

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
                {"role": "user", "content": prompt["user"]},
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
