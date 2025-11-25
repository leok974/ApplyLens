"""
Gemini integration wrapper for email processing.

Integrates Gemini classification and extraction into the existing ApplyLens
email processing pipeline with Datadog observability.
"""

import logging
import os
from typing import Dict, Any, Optional
from app.llm.gemini_client import get_gemini_client
from app.routers.debug_llm import log_llm_call

logger = logging.getLogger(__name__)


async def classify_email_with_gemini(
    subject: str,
    snippet: str,
    sender: str,
) -> Optional[Dict[str, Any]]:
    """
    Classify email using Gemini if enabled, otherwise return None.

    Returns:
        Classification result or None if disabled/failed
    """
    if not os.getenv("USE_GEMINI_FOR_CLASSIFY"):
        return None

    client = get_gemini_client()
    if not client:
        return None

    try:
        result = await client.classify_email_intent(subject, snippet, sender)

        # Log for debug endpoint
        log_llm_call(
            task_type="classify",
            model_used=result.get("model_used", "unknown"),
            latency_ms=result.get("latency_ms", 0),
            success=True,
        )

        return result
    except Exception as e:
        logger.error(f"Gemini classification failed: {e}", exc_info=True)
        log_llm_call(
            task_type="classify",
            model_used="error",
            latency_ms=0,
            success=False,
            error_msg=str(e),
        )
        return None


async def extract_entities_with_gemini(
    subject: str,
    body_snippet: str,
) -> Optional[Dict[str, Any]]:
    """
    Extract job entities using Gemini if enabled, otherwise return None.

    Returns:
        Extraction result or None if disabled/failed
    """
    if not os.getenv("USE_GEMINI_FOR_EXTRACT"):
        return None

    client = get_gemini_client()
    if not client:
        return None

    try:
        result = await client.extract_job_entities(subject, body_snippet)

        # Log for debug endpoint
        log_llm_call(
            task_type="extract",
            model_used=result.get("model_used", "unknown"),
            latency_ms=result.get("latency_ms", 0),
            success=True,
        )

        return result
    except Exception as e:
        logger.error(f"Gemini extraction failed: {e}", exc_info=True)
        log_llm_call(
            task_type="extract",
            model_used="error",
            latency_ms=0,
            success=False,
            error_msg=str(e),
        )
        return None


def enrich_email_with_gemini_data(
    email_dict: Dict[str, Any],
    classification: Optional[Dict],
    extraction: Optional[Dict],
) -> Dict[str, Any]:
    """
    Enrich email dictionary with Gemini classification and extraction results.

    Adds fields:
    - gemini_intent: Classified intent
    - gemini_confidence: Classification confidence
    - gemini_company: Extracted company
    - gemini_role: Extracted role
    - gemini_model_used: Which model was used (gemini vs heuristic)
    """
    if classification:
        email_dict["gemini_intent"] = classification.get("intent")
        email_dict["gemini_confidence"] = classification.get("confidence")
        email_dict["gemini_classification_model"] = classification.get("model_used")

    if extraction:
        email_dict["gemini_company"] = extraction.get("company")
        email_dict["gemini_role"] = extraction.get("role")
        email_dict["gemini_recruiter"] = extraction.get("recruiter_name")
        email_dict["gemini_interview_date"] = extraction.get("interview_date")
        email_dict["gemini_extraction_model"] = extraction.get("model_used")

    return email_dict
