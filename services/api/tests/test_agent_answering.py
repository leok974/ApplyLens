"""
Golden tests for agent answering module - Zero-results phrasing validation.

These tests verify that LLM answers for scan intents handle count=0 correctly:
- Should NOT reference "card below" / "list below" when count=0
- Should use phrases like "all caught up" / "didn't find any"

NOTE: These are integration tests that require actual LLM (Ollama/OpenAI) access.
Skip if LLM is not available.
"""

import pytest
import os
from unittest.mock import MagicMock

from app.agent.answering import complete_agent_answer
from app.schemas_agent import AgentCard


# Skip all tests if LLM is not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("OLLAMA_BASE") and not os.getenv("OPENAI_API_KEY"),
    reason="LLM not configured (need OLLAMA_BASE or OPENAI_API_KEY)",
)


@pytest.fixture
def mock_dependencies():
    """Mock dependencies for complete_agent_answer"""
    return {
        "db": MagicMock(),
        "user_id": "test_user",
        "query_text": "test query",
        "email_context": [],
        "latest_agent_response": None,
        "agent_manager": MagicMock(),
    }


# --- ZERO-RESULTS VALIDATION TESTS ---


@pytest.mark.asyncio
async def test_followups_zero_results_no_card_reference(mock_dependencies):
    """followups with count=0 should NOT mention 'card below'"""
    tool_cards = [
        AgentCard(
            kind="followups_summary",
            meta={"count": 0, "time_window_days": 90},
            data={},
        )
    ]

    answer, _ = await complete_agent_answer(
        **mock_dependencies,
        intent="followups",
        tool_cards=tool_cards,
    )

    # Assert count=0 phrasing
    assert (
        "0" in answer
        or "didn't find" in answer.lower()
        or "no conversations" in answer.lower()
        or "caught up" in answer.lower()
    )

    # Assert NO card reference when count=0
    assert "card below" not in answer.lower()
    assert "listed below" not in answer.lower()


@pytest.mark.asyncio
async def test_unsubscribe_zero_results_no_list_reference(mock_dependencies):
    """unsubscribe with count=0 should NOT mention list"""
    tool_cards = [
        AgentCard(
            kind="unsubscribe_summary",
            meta={"count": 0, "time_window_days": 30},
            data={},
        )
    ]

    answer, _ = await complete_agent_answer(
        **mock_dependencies,
        intent="unsubscribe",
        tool_cards=tool_cards,
    )

    assert (
        "caught up" in answer.lower()
        or "0" in answer
        or "no" in answer.lower()
        or "didn't find" in answer.lower()
    )
    assert "list below" not in answer.lower()
    assert "see the list" not in answer.lower()


@pytest.mark.asyncio
async def test_suspicious_zero_results_no_card_reference(mock_dependencies):
    """suspicious with count=0 should NOT mention card"""
    tool_cards = [
        AgentCard(
            kind="suspicious_summary",
            meta={"count": 0, "time_window_days": 7},
            data={},
        )
    ]

    answer, _ = await complete_agent_answer(
        **mock_dependencies,
        intent="suspicious",
        tool_cards=tool_cards,
    )

    assert "didn't find" in answer.lower() or "0" in answer or "no" in answer.lower()
    assert "card below" not in answer.lower()


@pytest.mark.asyncio
async def test_bills_zero_results_no_card_reference(mock_dependencies):
    """bills with count=0 should NOT mention card"""
    tool_cards = [
        AgentCard(
            kind="bills_summary",
            meta={"count": 0, "time_window_days": 30},
            data={},
        )
    ]

    answer, _ = await complete_agent_answer(
        **mock_dependencies,
        intent="bills",
        tool_cards=tool_cards,
    )

    assert (
        "caught up" in answer.lower() or "0" in answer or "no bills" in answer.lower()
    )
    assert "card below" not in answer.lower()


@pytest.mark.asyncio
async def test_interviews_zero_results_no_card_reference(mock_dependencies):
    """interviews with count=0 should NOT mention card"""
    tool_cards = [
        AgentCard(
            kind="interviews_summary",
            meta={"count": 0, "time_window_days": 14},
            data={},
        )
    ]

    answer, _ = await complete_agent_answer(
        **mock_dependencies,
        intent="interviews",
        tool_cards=tool_cards,
    )

    assert (
        "caught up" in answer.lower()
        or "0" in answer
        or "no interview" in answer.lower()
        or "didn't find" in answer.lower()
    )
    assert "card below" not in answer.lower()


@pytest.mark.asyncio
async def test_clean_promos_zero_results_no_card_reference(mock_dependencies):
    """clean_promos with count=0 should NOT mention card"""
    tool_cards = [
        AgentCard(
            kind="clean_promos_summary",
            meta={"count": 0, "time_window_days": 60},
            data={},
        )
    ]

    answer, _ = await complete_agent_answer(
        **mock_dependencies,
        intent="clean_promos",
        tool_cards=tool_cards,
    )

    assert (
        "caught up" in answer.lower()
        or "0" in answer
        or "no promotional" in answer.lower()
        or "didn't find" in answer.lower()
    )
    assert "card below" not in answer.lower()


# --- POSITIVE RESULTS VALIDATION ---


@pytest.mark.asyncio
async def test_followups_with_results_references_card(mock_dependencies):
    """followups with count>0 SHOULD reference card and exact numbers"""
    tool_cards = [
        AgentCard(
            kind="followups_summary",
            meta={"count": 3, "time_window_days": 30},
            data={},
        )
    ]

    answer, _ = await complete_agent_answer(
        **mock_dependencies,
        intent="followups",
        tool_cards=tool_cards,
    )

    # Assert answer contains exact count
    assert "3" in answer

    # Assert answer references card (should say "below" or "listed" when count>0)
    assert "below" in answer.lower() or "listed" in answer.lower()


@pytest.mark.asyncio
async def test_unsubscribe_with_results_references_list(mock_dependencies):
    """unsubscribe with count>0 should reference list"""
    tool_cards = [
        AgentCard(
            kind="unsubscribe_summary",
            meta={"count": 9, "time_window_days": 90},
            data={},
        )
    ]

    answer, _ = await complete_agent_answer(
        **mock_dependencies,
        intent="unsubscribe",
        tool_cards=tool_cards,
    )

    assert "9" in answer
    assert "below" in answer.lower() or "list" in answer.lower()


# --- HALLUCINATION PREVENTION ---


@pytest.mark.asyncio
async def test_no_fabricated_company_names(mock_dependencies):
    """Verify answer does NOT contain common hallucinated company names"""
    tool_cards = [
        AgentCard(
            kind="followups_summary",
            meta={"count": 2, "time_window_days": 30},
            data={},
        )
    ]

    answer, _ = await complete_agent_answer(
        **mock_dependencies,
        intent="followups",
        tool_cards=tool_cards,
    )

    # Forbidden hallucinations
    forbidden = [
        "Company A",
        "Company B",
        "Company C",
        "Acme Corp",
        "[Insert Date]",
    ]

    for term in forbidden:
        assert (
            term not in answer
        ), f"Answer contains forbidden hallucinated term: {term}"
