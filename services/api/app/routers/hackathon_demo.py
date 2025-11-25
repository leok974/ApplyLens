"""
Hackathon demo endpoint for Gemini classification.

Provides a simple test interface to demonstrate Gemini + Datadog integration.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.llm.integration import classify_email_with_gemini, extract_entities_with_gemini

router = APIRouter(prefix="/hackathon", tags=["hackathon"])


class EmailSample(BaseModel):
    """Sample email for classification/extraction."""

    subject: str
    snippet: str
    sender: str = "recruiter@example.com"


class ClassificationResponse(BaseModel):
    """Classification result."""

    intent: str
    confidence: float
    reasoning: str
    model_used: str
    latency_ms: int


class ExtractionResponse(BaseModel):
    """Extraction result."""

    company: Optional[str]
    role: Optional[str]
    recruiter_name: Optional[str]
    interview_date: Optional[str]
    salary_mentioned: bool
    model_used: str
    latency_ms: int


class CombinedResponse(BaseModel):
    """Combined classification and extraction."""

    classification: ClassificationResponse
    extraction: ExtractionResponse


@router.post("/classify", response_model=ClassificationResponse)
async def test_classify_email(email: EmailSample):
    """
    Test endpoint: Classify email intent using Gemini.

    Example:
    ```
    POST /hackathon/classify
    {
      "subject": "Interview invitation for Senior Engineer role",
      "snippet": "We'd like to schedule a call to discuss the opportunity...",
      "sender": "recruiter@techcorp.com"
    }
    ```
    """
    result = await classify_email_with_gemini(
        subject=email.subject,
        snippet=email.snippet,
        sender=email.sender,
    )

    if not result:
        raise HTTPException(
            status_code=503,
            detail="Gemini classification not available (check USE_GEMINI_FOR_CLASSIFY and GOOGLE_CLOUD_PROJECT)",
        )

    return ClassificationResponse(**result)


@router.post("/extract", response_model=ExtractionResponse)
async def test_extract_entities(email: EmailSample):
    """
    Test endpoint: Extract job entities using Gemini.

    Example:
    ```
    POST /hackathon/extract
    {
      "subject": "Senior Software Engineer at Google",
      "snippet": "Hi Jane, I'm reaching out about a senior engineering role at Google Cloud...",
      "sender": "john.smith@google.com"
    }
    ```
    """
    result = await extract_entities_with_gemini(
        subject=email.subject,
        body_snippet=email.snippet,
    )

    if not result:
        raise HTTPException(
            status_code=503,
            detail="Gemini extraction not available (check USE_GEMINI_FOR_EXTRACT and GOOGLE_CLOUD_PROJECT)",
        )

    return ExtractionResponse(**result)


@router.post("/analyze", response_model=CombinedResponse)
async def test_analyze_email(email: EmailSample):
    """
    Test endpoint: Full email analysis (classify + extract).

    Demonstrates complete Gemini pipeline with Datadog tracing.
    """
    # Run classification and extraction in parallel
    import asyncio

    classification_task = classify_email_with_gemini(
        subject=email.subject,
        snippet=email.snippet,
        sender=email.sender,
    )

    extraction_task = extract_entities_with_gemini(
        subject=email.subject,
        body_snippet=email.snippet,
    )

    classification, extraction = await asyncio.gather(
        classification_task,
        extraction_task,
    )

    if not classification or not extraction:
        raise HTTPException(
            status_code=503, detail="Gemini not available (check environment variables)"
        )

    return CombinedResponse(
        classification=ClassificationResponse(**classification),
        extraction=ExtractionResponse(**extraction),
    )
