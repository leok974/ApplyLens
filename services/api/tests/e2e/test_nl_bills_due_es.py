"""
End-to-end tests for NL bills due integration.

Tests the complete flow:
1. User sends "bills due before Friday" command
2. System parses date cutoff
3. System queries Elasticsearch for bills
4. System creates reminders for each bill
5. System audits reminder creation
"""

import pytest
from httpx import AsyncClient

import app.logic.audit_es as AUD
import app.logic.search as S
from app.main import app


@pytest.mark.asyncio
async def test_nl_bills_due_before_friday(monkeypatch):
    """Test complete NL flow for 'bills due before Friday'."""
    # Capture emitted audit events
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))

    # Mock ES to return two bills
    async def fake_bills(cutoff_iso: str, limit: int = 200):
        return [
            {
                "id": "billA",
                "category": "bills",
                "subject": "Credit card bill",
                "sender_domain": "bank.example.com",
                "dates": ["2025-10-11T00:00:00Z"],
                "money_amounts": [{"amount": 250.00, "currency": "USD"}],
                "received_at": "2025-10-01T10:00:00Z",
            },
            {
                "id": "billB",
                "category": "bills",
                "subject": "Phone bill",
                "sender_domain": "telecom.example.com",
                "expires_at": "2025-10-09T00:00:00Z",
                "money_amounts": [{"amount": 75.50, "currency": "USD"}],
                "received_at": "2025-09-28T12:00:00Z",
            },
        ]

    monkeypatch.setattr(S, "find_bills_due_before", fake_bills)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post(
            "/nl/run",
            json={"text": "show my bills due before Friday and create reminders"},
        )

        assert r.status_code == 200
        j = r.json()

        # Verify response structure
        assert j["intent"] == "summarize_bills"
        assert j["created"] == 2
        assert j["count"] == 2
        assert "cutoff" in j

        # Verify reminders were created
        reminders = j["reminders"]
        assert len(reminders) == 2

        # Check first reminder
        r1 = next((r for r in reminders if r["email_id"] == "billA"), None)
        assert r1 is not None
        assert "Credit card bill" in r1["title"]
        assert "$250.00" in r1["title"]
        assert r1["due_at"] == "2025-10-11T00:00:00Z"

        # Check second reminder
        r2 = next((r for r in reminders if r["email_id"] == "billB"), None)
        assert r2 is not None
        assert "Phone bill" in r2["title"]
        assert "$75.50" in r2["title"]
        assert r2["due_at"] == "2025-10-09T00:00:00Z"

        # Verify audit events were emitted
        reminder_audits = [x for x in emitted if x.get("action") == "create_reminder"]
        assert len(reminder_audits) == 2


@pytest.mark.asyncio
async def test_nl_bills_no_results(monkeypatch):
    """Test NL flow when no bills match the query."""
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))

    # Mock ES to return empty results
    async def fake_bills(cutoff_iso: str, limit: int = 200):
        return []

    monkeypatch.setattr(S, "find_bills_due_before", fake_bills)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/nl/run", json={"text": "bills due by Monday"})

        assert r.status_code == 200
        j = r.json()

        assert j["intent"] == "summarize_bills"
        assert j["count"] == 0
        assert j["created"] == 1  # Fallback reminder created

        # Verify fallback reminder
        reminders = j["reminders"]
        assert len(reminders) == 1
        assert "No bills found" in reminders[0]["title"]


@pytest.mark.asyncio
async def test_nl_bills_explicit_date_format(monkeypatch):
    """Test NL flow with explicit date format 'by 10/15'."""
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))

    # Mock ES to return one bill
    async def fake_bills(cutoff_iso: str, limit: int = 200):
        # Verify cutoff was parsed correctly
        assert "2025-10-15" in cutoff_iso
        return [
            {
                "id": "bill_explicit",
                "category": "bills",
                "subject": "Utility bill",
                "sender_domain": "utility.example.com",
                "dates": ["2025-10-14T00:00:00Z"],
                "money_amounts": [],
                "received_at": "2025-10-01T10:00:00Z",
            }
        ]

    monkeypatch.setattr(S, "find_bills_due_before", fake_bills)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/nl/run", json={"text": "show bills due by 10/15/2025"})

        assert r.status_code == 200
        j = r.json()

        assert j["intent"] == "summarize_bills"
        assert j["count"] == 1
        assert "2025-10-15" in j["cutoff"]


@pytest.mark.asyncio
async def test_nl_bills_named_month_format(monkeypatch):
    """Test NL flow with named month format 'before Oct 20, 2025'."""
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))

    # Mock ES
    async def fake_bills(cutoff_iso: str, limit: int = 200):
        assert "2025-10-20" in cutoff_iso
        return [
            {
                "id": "bill_named",
                "category": "bills",
                "subject": "Insurance bill",
                "sender_domain": "insurance.example.com",
                "expires_at": "2025-10-18T00:00:00Z",
                "money_amounts": [{"amount": 500.00, "currency": "USD"}],
                "received_at": "2025-09-20T10:00:00Z",
            }
        ]

    monkeypatch.setattr(S, "find_bills_due_before", fake_bills)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/nl/run", json={"text": "bills due before Oct 20, 2025"})

        assert r.status_code == 200
        j = r.json()

        assert j["intent"] == "summarize_bills"
        assert j["count"] == 1

        reminder = j["reminders"][0]
        assert "Insurance bill" in reminder["title"]
        assert "$500.00" in reminder["title"]


@pytest.mark.asyncio
async def test_nl_bills_with_missing_money_amounts(monkeypatch):
    """Test NL flow with bills that have no money amounts."""
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))

    async def fake_bills(cutoff_iso: str, limit: int = 200):
        return [
            {
                "id": "bill_no_money",
                "category": "bills",
                "subject": "Bill without amount",
                "sender_domain": "sender.example.com",
                "dates": ["2025-10-10T00:00:00Z"],
                "money_amounts": [],  # Empty
                "received_at": "2025-10-01T10:00:00Z",
            }
        ]

    monkeypatch.setattr(S, "find_bills_due_before", fake_bills)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/nl/run", json={"text": "bills due before Friday"})

        assert r.status_code == 200
        j = r.json()

        reminder = j["reminders"][0]
        assert "Bill without amount" in reminder["title"]
        # Should not crash with missing money amounts
        assert "$" not in reminder["title"] or reminder["title"].endswith(" - $")


@pytest.mark.asyncio
async def test_nl_bills_without_date_phrase(monkeypatch):
    """Test NL flow when date phrase cannot be parsed."""
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))

    # Mock ES - should not be called if cutoff is None
    call_count = {"count": 0}

    async def fake_bills(cutoff_iso: str, limit: int = 200):
        call_count["count"] += 1
        return []

    monkeypatch.setattr(S, "find_bills_due_before", fake_bills)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post(
            "/nl/run", json={"text": "show me bills"}  # No "before" or "by" phrase
        )

        assert r.status_code == 200
        j = r.json()

        assert j["intent"] == "summarize_bills"
        assert j["cutoff"] is None
        assert call_count["count"] == 0  # ES not called

        # Fallback reminder created
        assert j["created"] == 1
        assert "No bills found" in j["reminders"][0]["title"]


@pytest.mark.asyncio
async def test_nl_bills_audit_contains_bill_metadata(monkeypatch):
    """Test that audit events contain relevant bill metadata."""
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))

    async def fake_bills(cutoff_iso: str, limit: int = 200):
        return [
            {
                "id": "bill_audit_test",
                "category": "bills",
                "subject": "Test bill",
                "sender_domain": "test.example.com",
                "dates": ["2025-10-12T00:00:00Z"],
                "money_amounts": [{"amount": 100.00, "currency": "USD"}],
                "received_at": "2025-10-01T10:00:00Z",
            }
        ]

    monkeypatch.setattr(S, "find_bills_due_before", fake_bills)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/nl/run", json={"text": "bills due before Friday"})

        assert r.status_code == 200

        # Find reminder audit event
        reminder_audit = next(
            (x for x in emitted if x.get("email_id") == "bill_audit_test"), None
        )

        assert reminder_audit is not None
        assert reminder_audit["action"] == "create_reminder"
        assert "Test bill" in reminder_audit.get("rationale", "")


@pytest.mark.asyncio
async def test_nl_bills_multiple_dates_in_array(monkeypatch):
    """Test bill with multiple dates in dates array."""
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))

    async def fake_bills(cutoff_iso: str, limit: int = 200):
        return [
            {
                "id": "bill_multi_dates",
                "category": "bills",
                "subject": "Bill with payment schedule",
                "sender_domain": "lender.example.com",
                "dates": [
                    "2025-10-10T00:00:00Z",  # First payment
                    "2025-11-10T00:00:00Z",  # Second payment
                    "2025-12-10T00:00:00Z",  # Third payment
                ],
                "money_amounts": [{"amount": 300.00, "currency": "USD"}],
                "received_at": "2025-09-25T10:00:00Z",
            }
        ]

    monkeypatch.setattr(S, "find_bills_due_before", fake_bills)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/nl/run", json={"text": "bills due before Friday"})

        assert r.status_code == 200
        j = r.json()

        reminder = j["reminders"][0]
        # Should use first date from array
        assert reminder["due_at"] == "2025-10-10T00:00:00Z"
        assert "Bill with payment schedule" in reminder["title"]
