"""Tests for LLM-powered resume profile extraction."""

import pytest
from app.services.resume_parser import (
    extract_profile_from_resume_llm,
    ExtractedProfile,
)


@pytest.mark.asyncio
@pytest.mark.llm  # Mark as LLM test (can be skipped in CI)
async def test_llm_extract_profile_shape():
    """Test that LLM extraction returns valid ExtractedProfile shape."""
    sample_text = """
Leo Klemet
AI/ML Engineer & Full-Stack Developer
Herndon, VA, US

GitHub: https://github.com/leok974
Portfolio: https://www.leoklemet.com
LinkedIn: https://linkedin.com/in/leoklemet

SUMMARY
Experienced AI/ML engineer specializing in agentic systems and full-stack development.
8+ years building production systems with Python, FastAPI, React, and modern ML frameworks.

SKILLS
Python, FastAPI, React, TypeScript, PostgreSQL, Elasticsearch, Docker, Kubernetes,
LLMs, LangChain, LangGraph, OpenAI, Ollama, Prometheus, Grafana

EXPERIENCE
Senior AI Engineer | ApplyLens | 2023 - Present
- Built agentic job-inbox with Gmail OAuth integration
- Implemented LLM-powered form completion for browser extension
- Designed Elasticsearch search with synonym/recency boosts
"""

    profile = await extract_profile_from_resume_llm(sample_text)

    # Verify shape and basic types
    assert isinstance(profile, ExtractedProfile)
    assert profile.full_name is None or isinstance(profile.full_name, str)
    assert profile.headline is None or isinstance(profile.headline, str)
    assert isinstance(profile.skills, list)
    assert isinstance(profile.top_roles, list)

    # Verify URL fields are strings or None
    assert profile.github_url is None or profile.github_url.startswith("http")
    assert profile.website_url is None or profile.website_url.startswith("http")
    assert profile.linkedin_url is None or profile.linkedin_url.startswith("http")

    # Don't assert exact content (LLM output varies), just that structure is correct
    print(
        f"Extracted: {profile.full_name}, {len(profile.skills)} skills, {len(profile.top_roles)} roles"
    )
