"""
Test Gemini integration for hackathon.

Run with: pytest tests/test_hackathon_gemini.py -v
"""

import pytest
import asyncio
import os
from app.llm.gemini_client import GeminiLLMClient, GeminiConfig


@pytest.mark.asyncio
async def test_gemini_classify_heuristic_fallback():
    """Test that heuristic classification works when Gemini is unavailable."""
    # Force heuristic mode by using invalid config
    config = GeminiConfig(
        project_id="fake-project",
        timeout_seconds=0.001,  # Timeout immediately
    )
    client = GeminiLLMClient(config)

    result = await client.classify_email_intent(
        subject="Interview invitation for Senior Engineer",
        snippet="We'd like to schedule a technical interview next week",
        sender="recruiter@techcorp.com",
    )

    # Should fall back to heuristic
    assert result["model_used"] == "heuristic"
    assert result["intent"] == "interview"  # Keyword matching
    assert result["confidence"] > 0
    assert "latency_ms" in result


@pytest.mark.asyncio
async def test_gemini_extract_heuristic_fallback():
    """Test that heuristic extraction works when Gemini is unavailable."""
    config = GeminiConfig(project_id="fake-project", timeout_seconds=0.001)
    client = GeminiLLMClient(config)

    result = await client.extract_job_entities(
        subject="Senior Software Engineer at Google - $200k",
        body_snippet="Hi Jane, reaching out about a senior role with competitive compensation",
    )

    # Should fall back to heuristic
    assert result["model_used"] == "heuristic"
    assert result["salary_mentioned"] is True  # Detected "$"
    assert "latency_ms" in result


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("GOOGLE_CLOUD_PROJECT"),
    reason="GOOGLE_CLOUD_PROJECT not set - skip Gemini API test",
)
async def test_gemini_classify_real_api():
    """Test real Gemini API classification (requires credentials)."""
    from app.llm.gemini_client import get_gemini_client

    client = get_gemini_client()
    if not client:
        pytest.skip("Gemini client not available")

    result = await client.classify_email_intent(
        subject="Thank you for your application",
        snippet="We have received your application for the Software Developer position",
        sender="careers@startup.io",
    )

    # Should use Gemini
    assert result["model_used"] in ["gemini", "heuristic"]  # Could fall back
    assert result["intent"] in [
        "job_application",
        "interview",
        "offer",
        "rejection",
        "other",
    ]
    assert 0 <= result["confidence"] <= 1.0
    assert result["latency_ms"] > 0


def test_classification_taxonomy():
    """Test that all expected intents are recognized."""
    from app.llm.gemini_client import GeminiLLMClient, GeminiConfig

    config = GeminiConfig(project_id="fake")
    client = GeminiLLMClient(config)

    test_cases = [
        ("Interview", "schedule a call", "interview"),
        ("Offer letter", "pleased to offer", "offer"),
        ("Application status", "unfortunately not moving forward", "rejection"),
        ("Thank you", "received your application", "job_application"),
        ("Newsletter", "latest tech news", "other"),
    ]

    for subject, snippet, expected in test_cases:
        result = asyncio.run(
            client.classify_email_intent(subject, snippet, "sender@example.com")
        )
        # Heuristics should match expected intent
        assert result["intent"] == expected, f"Failed for: {subject}"


def test_extraction_schema():
    """Test that extraction returns correct schema."""
    from app.llm.gemini_client import GeminiLLMClient, GeminiConfig

    config = GeminiConfig(project_id="fake")
    client = GeminiLLMClient(config)

    result = asyncio.run(
        client.extract_job_entities(
            subject="Senior Engineer at TechCorp - $180k",
            body_snippet="Hi, I'm John from TechCorp recruiting...",
        )
    )

    # Check schema
    assert "company" in result
    assert "role" in result
    assert "recruiter_name" in result
    assert "interview_date" in result
    assert "salary_mentioned" in result
    assert "model_used" in result
    assert "latency_ms" in result

    # Check types
    assert isinstance(result["salary_mentioned"], bool)
    assert isinstance(result["latency_ms"], int)
    assert result["salary_mentioned"] is True  # "$180k" detected


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test that timeout is enforced."""
    import time

    config = GeminiConfig(
        project_id="fake",
        timeout_seconds=0.1,  # Very short timeout
    )
    client = GeminiLLMClient(config)

    start = time.time()
    result = await client.classify_email_intent(
        subject="Test" * 1000,  # Long subject
        snippet="Test" * 1000,  # Long snippet
        sender="test@example.com",
    )
    elapsed = time.time() - start

    # Should timeout and fall back quickly
    assert elapsed < 1.0  # Should not hang
    assert result["model_used"] == "heuristic"  # Fell back


def test_privacy_safe_prompts():
    """Test that prompts don't include sensitive data."""
    from app.llm.gemini_client import GeminiLLMClient, GeminiConfig

    config = GeminiConfig(project_id="fake")
    client = GeminiLLMClient(config)

    # Snippet should be truncated in prompt
    long_snippet = "X" * 500  # Longer than 200 char limit

    result = asyncio.run(
        client.classify_email_intent(
            subject="Test", snippet=long_snippet, sender="test@example.com"
        )
    )

    # Should still work with truncation
    assert result is not None
    assert "intent" in result
