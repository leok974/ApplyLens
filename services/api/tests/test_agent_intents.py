"""
Tests for Agent V2 intent-driven behavior contracts.

Validates that each intent follows its spec:
- Correct metrics fields
- Correct card IDs and titles
- Zero vs non-zero result handling
"""

import pytest
from typing import Dict, Any

from app.agent.orchestrator import MailboxAgentOrchestrator, INTENT_SPECS
from app.schemas_agent import ToolResult


class MockToolRegistry:
    """Mock tool registry for testing."""

    def __init__(self, mock_results: Dict[str, Any]):
        self.mock_results = mock_results

    async def run_tool(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Return mocked tool result."""
        if tool_name in self.mock_results:
            return ToolResult(
                tool_name=tool_name,
                status="success",
                summary=f"{tool_name} executed successfully",
                data=self.mock_results[tool_name],
                duration_ms=100,
            )
        return ToolResult(
            tool_name=tool_name,
            status="error",
            summary=f"{tool_name} not mocked",
            data={},
            duration_ms=0,
        )


@pytest.mark.asyncio
async def test_suspicious_zero_results_builds_zero_card():
    """Test suspicious intent with zero matches builds correct zero-result card."""

    # Mock tools to return zero suspicious emails
    mock_tools = MockToolRegistry(
        {
            "email_search": {
                "emails": [],
                "count": 0,
            },
            "security_scan": {
                "emails_scanned": 50,
                "matches": [],
                "high_risk_count": 0,
            },
        }
    )

    orch = MailboxAgentOrchestrator(tool_registry=mock_tools)
    spec = INTENT_SPECS["suspicious"]

    # Simulate tool results
    tool_results = [
        ToolResult(
            tool_name="email_search",
            status="success",
            summary="Searched 50 emails",
            data=mock_tools.mock_results["email_search"],
            duration_ms=200,
        ),
        ToolResult(
            tool_name="security_scan",
            status="success",
            summary="Scanned 50 emails, found 0 suspicious",
            data=mock_tools.mock_results["security_scan"],
            duration_ms=300,
        ),
    ]

    # Build metrics
    metrics = orch._build_metrics_from_spec(spec, tool_results, time_window_days=30)

    # Validate metrics
    assert metrics["emails_scanned"] == 50
    assert metrics["matches"] == 0
    assert metrics["high_risk"] == 0
    assert metrics["time_window_days"] == 30

    # Build cards
    cards = orch._build_cards_from_spec(
        spec, tool_results, metrics, time_window_days=30
    )

    # Validate card structure
    assert len(cards) == 1
    card = cards[0]
    assert card.kind == "suspicious_summary"
    assert card.title == "No Suspicious Emails Found"
    assert card.meta["count"] == 0
    assert card.meta["time_window_days"] == 30
    assert len(card.email_ids) == 0


@pytest.mark.asyncio
async def test_suspicious_nonzero_results_builds_match_card():
    """Test suspicious intent with matches builds correct non-zero card."""

    # Mock tools to return 3 suspicious emails
    mock_matches = [
        {
            "message_id": "msg1",
            "subject": "Urgent: Verify your account",
            "from_address": "phish@example.com",
            "risk_level": "high",
            "reasons": ["Suspicious link", "Urgent language"],
            "received_at": "2025-11-20T10:00:00Z",
        },
        {
            "message_id": "msg2",
            "subject": "You won the lottery!",
            "from_address": "scam@bad.com",
            "risk_level": "high",
            "reasons": ["Too good to be true", "Unknown sender"],
            "received_at": "2025-11-19T15:30:00Z",
        },
        {
            "message_id": "msg3",
            "subject": "Invoice payment required",
            "from_address": "fake@invoice.net",
            "risk_level": "medium",
            "reasons": ["Fake invoice pattern"],
            "received_at": "2025-11-18T09:15:00Z",
        },
    ]

    mock_tools = MockToolRegistry(
        {
            "email_search": {
                "emails": mock_matches,
                "count": 3,
            },
            "security_scan": {
                "emails_scanned": 50,
                "matches": mock_matches,
                "high_risk_count": 2,
            },
        }
    )

    orch = MailboxAgentOrchestrator(tool_registry=mock_tools)
    spec = INTENT_SPECS["suspicious"]

    tool_results = [
        ToolResult(
            tool_name="security_scan",
            status="success",
            summary="Found 3 suspicious emails",
            data=mock_tools.mock_results["security_scan"],
            duration_ms=300,
        ),
    ]

    metrics = orch._build_metrics_from_spec(spec, tool_results, time_window_days=30)

    # Validate metrics
    assert metrics["emails_scanned"] == 50
    assert metrics["matches"] == 3
    assert metrics["high_risk"] == 2

    # Build cards
    cards = orch._build_cards_from_spec(
        spec, tool_results, metrics, time_window_days=30
    )

    # Validate card
    assert len(cards) == 1
    card = cards[0]
    assert card.kind == "suspicious_summary"
    assert card.title == "Suspicious Emails Found"
    assert card.meta["count"] == 3
    assert len(card.email_ids) == 3

    # Validate items structure
    items = card.meta.get("items", [])
    assert len(items) == 3
    assert items[0]["risk_level"] == "high"
    assert "Suspicious link" in items[0]["reasons"]
    assert items[1]["subject"] == "You won the lottery!"


@pytest.mark.asyncio
async def test_followups_zero_results():
    """Test followups intent with no conversations needing reply."""

    mock_tools = MockToolRegistry(
        {
            "email_search": {
                "threads": [
                    {"thread_id": "t1", "replied": True},
                    {"thread_id": "t2", "replied": True},
                ],
                "count": 2,
            },
        }
    )

    orch = MailboxAgentOrchestrator(tool_registry=mock_tools)
    spec = INTENT_SPECS["followups"]

    tool_results = [
        ToolResult(
            tool_name="email_search",
            status="success",
            summary="Found 2 threads, all replied",
            data=mock_tools.mock_results["email_search"],
            duration_ms=200,
        ),
    ]

    metrics = orch._build_metrics_from_spec(spec, tool_results, time_window_days=30)

    assert metrics["conversations_scanned"] == 2
    assert metrics["needs_reply"] == 0

    cards = orch._build_cards_from_spec(
        spec, tool_results, metrics, time_window_days=30
    )

    assert len(cards) == 1
    assert cards[0].kind == "followups_summary"
    assert cards[0].title == "No Conversations Need Follow-up"
    assert cards[0].meta["count"] == 0


@pytest.mark.asyncio
async def test_followups_nonzero_results():
    """Test followups intent with conversations needing reply."""

    unreplied_threads = [
        {
            "thread_id": "t1",
            "replied": False,
            "company": "TechCorp",
            "subject": "Interview invitation",
            "last_from": "recruiter",
            "last_received_at": "2025-11-18T14:00:00Z",
            "suggested_angle": "Confirm interest and availability",
        },
        {
            "thread_id": "t2",
            "replied": False,
            "company": "StartupXYZ",
            "subject": "Technical assessment",
            "last_from": "hiring_manager",
            "last_received_at": "2025-11-17T10:00:00Z",
            "suggested_angle": "Ask for timeline clarification",
        },
    ]

    all_threads = unreplied_threads + [{"thread_id": "t3", "replied": True}]

    mock_tools = MockToolRegistry(
        {
            "email_search": {
                "threads": all_threads,
                "count": 3,
            },
        }
    )

    orch = MailboxAgentOrchestrator(tool_registry=mock_tools)
    spec = INTENT_SPECS["followups"]

    tool_results = [
        ToolResult(
            tool_name="email_search",
            status="success",
            summary="Found 2 unreplied threads",
            data=mock_tools.mock_results["email_search"],
            duration_ms=200,
        ),
    ]

    metrics = orch._build_metrics_from_spec(spec, tool_results, time_window_days=30)

    assert metrics["conversations_scanned"] == 3
    assert metrics["needs_reply"] == 2

    cards = orch._build_cards_from_spec(
        spec, tool_results, metrics, time_window_days=30
    )

    assert len(cards) == 1
    card = cards[0]
    assert card.kind == "followups_summary"
    assert card.title == "Conversations Waiting on Your Reply"
    assert card.meta["count"] == 2

    items = card.meta.get("items", [])
    assert len(items) == 2
    assert items[0]["company"] == "TechCorp"
    assert items[1]["last_from"] == "hiring_manager"


@pytest.mark.asyncio
async def test_bills_zero_results():
    """Test bills intent with no bills found."""

    mock_tools = MockToolRegistry(
        {
            "email_search": {
                "bills": [],
                "count": 0,
            },
        }
    )

    orch = MailboxAgentOrchestrator(tool_registry=mock_tools)
    spec = INTENT_SPECS["bills"]

    tool_results = [
        ToolResult(
            tool_name="email_search",
            status="success",
            summary="No bills found",
            data=mock_tools.mock_results["email_search"],
            duration_ms=200,
        ),
    ]

    metrics = orch._build_metrics_from_spec(spec, tool_results, time_window_days=60)

    assert metrics["total_bills"] == 0
    assert metrics["due_soon"] == 0
    assert metrics["overdue"] == 0
    assert metrics["other"] == 0

    cards = orch._build_cards_from_spec(
        spec, tool_results, metrics, time_window_days=60
    )

    assert len(cards) == 1
    assert cards[0].kind == "bills_summary"
    assert cards[0].title == "No Bills Found"
    assert cards[0].meta["total"] == 0


@pytest.mark.asyncio
async def test_bills_nonzero_with_sections():
    """Test bills intent with bills in different sections."""

    mock_bills = [
        {
            "id": "b1",
            "merchant": "Electric Co",
            "amount": 150,
            "due_date": "2025-11-22",
            "status": "due_soon",
        },
        {
            "id": "b2",
            "merchant": "Internet ISP",
            "amount": 80,
            "due_date": "2025-11-23",
            "status": "due_soon",
        },
        {
            "id": "b3",
            "merchant": "Credit Card",
            "amount": 500,
            "due_date": "2025-11-15",
            "status": "overdue",
        },
        {
            "id": "b4",
            "merchant": "Phone Bill",
            "amount": 60,
            "due_date": "2025-12-01",
            "status": "upcoming",
        },
    ]

    mock_tools = MockToolRegistry(
        {
            "email_search": {
                "bills": mock_bills,
                "count": 4,
            },
        }
    )

    orch = MailboxAgentOrchestrator(tool_registry=mock_tools)
    spec = INTENT_SPECS["bills"]

    tool_results = [
        ToolResult(
            tool_name="email_search",
            status="success",
            summary="Found 4 bills",
            data=mock_tools.mock_results["email_search"],
            duration_ms=200,
        ),
    ]

    metrics = orch._build_metrics_from_spec(spec, tool_results, time_window_days=60)

    assert metrics["total_bills"] == 4
    assert metrics["due_soon"] == 2
    assert metrics["overdue"] == 1
    assert metrics["other"] == 1

    cards = orch._build_cards_from_spec(
        spec, tool_results, metrics, time_window_days=60
    )

    assert len(cards) == 1
    card = cards[0]
    assert card.kind == "bills_summary"
    assert card.title == "Bills Overview"
    assert card.meta["total"] == 4
    assert card.meta["due_soon"] == 2
    assert card.meta["overdue"] == 1

    # Validate sections
    sections = card.meta.get("sections", [])
    assert len(sections) == 3

    due_soon_section = next(s for s in sections if s["id"] == "due_soon")
    assert due_soon_section["title"] == "Due soon (next 7 days)"
    assert len(due_soon_section["items"]) == 2

    overdue_section = next(s for s in sections if s["id"] == "overdue")
    assert len(overdue_section["items"]) == 1
