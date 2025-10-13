"""
E2E tests for productivity tools (reminders and calendar events).
"""
import pytest
import app.logic.audit_es as AUD

@pytest.mark.asyncio
async def test_create_reminders_emits_audit(monkeypatch, async_client):
    """
    Test that creating reminders emits audit trail events.
    """
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))

    payload = {
        "items": [
            {
                "email_id": "bill_1",
                "title": "Pay electric bill",
                "due_at": "2025-10-12T17:00:00Z",
                "notes": "due soon"
            }
        ]
    }
        
    r = await async_client.post("/productivity/reminders/create", json=payload)
        
    assert r.status_code == 200
    assert r.json()["created"] == 1
        
    # Verify audit trail
    assert len(emitted) == 1
    assert emitted[0]["action"] == "create_reminder"
    assert emitted[0]["email_id"] == "bill_1"
    assert emitted[0]["actor"] == "agent"
    assert emitted[0]["policy_id"] == "calendar-reminder"

@pytest.mark.asyncio
async def test_create_multiple_reminders(monkeypatch, async_client):
    """
    Test creating multiple reminders in one request.
    """
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))

    payload = {
        "items": [
            {
                "email_id": "bill_1",
                "title": "Pay electric bill",
                "due_at": "2025-10-12T17:00:00Z"
            },
            {
                "email_id": "bill_2",
                "title": "Pay water bill",
                "due_at": "2025-10-15T17:00:00Z"
            },
            {
                "email_id": "bill_3",
                "title": "Pay internet bill",
                "due_at": "2025-10-18T17:00:00Z"
            }
        ]
    }
        
    r = await async_client.post("/productivity/reminders/create", json=payload)
        
    assert r.status_code == 200
    assert r.json()["created"] == 3
        
    # Verify all emitted
    assert len(emitted) == 3
    titles = [e["payload"]["title"] for e in emitted]
    assert "Pay electric bill" in titles
    assert "Pay water bill" in titles
    assert "Pay internet bill" in titles

@pytest.mark.asyncio
async def test_create_reminders_empty_list(async_client):
    """
    Test that empty reminder list returns error.
    """
    payload = {"items": []}
        
    r = await async_client.post("/productivity/reminders/create", json=payload)
        
    assert r.status_code == 400
    assert "No reminders" in r.json()["detail"]

@pytest.mark.asyncio
async def test_create_calendar_events(monkeypatch, async_client):
    """
    Test creating calendar events.
    """
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))

    payload = {
        "items": [
            {
                "email_id": "invite_1",
                "title": "Team Meeting",
                "start_time": "2025-10-12T14:00:00Z",
                "end_time": "2025-10-12T15:00:00Z",
                "location": "Conference Room A",
                "attendees": ["alice@example.com", "bob@example.com"]
            }
        ]
    }
        
    r = await async_client.post("/productivity/calendar/create", json=payload)
        
    assert r.status_code == 200
    assert r.json()["created"] == 1
        
    # Verify audit trail
    assert len(emitted) == 1
    assert emitted[0]["action"] == "create_calendar_event"
    assert emitted[0]["payload"]["title"] == "Team Meeting"
    assert emitted[0]["payload"]["location"] == "Conference Room A"

@pytest.mark.asyncio
async def test_nl_bills_creates_reminder(monkeypatch, async_client):
    """
    Test that NL agent can create reminders for bills.
    
    This tests the integration between /nl/run and /productivity/reminders/create.
    """
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))
    
    r = await async_client.post(
        "/nl/run",
        json={"text": "show my bills and create reminders due before Friday"}
    )
        
    assert r.status_code == 200
    j = r.json()
        
    assert j["intent"] == "summarize_bills"
    assert j["created"] >= 1
        
    # Verify reminder was created in audit trail
    assert any(x["action"] == "create_reminder" for x in emitted)

@pytest.mark.asyncio
async def test_reminder_with_optional_fields(monkeypatch, async_client):
    """
    Test creating reminder with minimal fields (optional fields omitted).
    """
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))

    payload = {
        "items": [
            {
                "email_id": "task_1",
                "title": "Follow up with client"
                # No due_at, source, or notes
            }
        ]
    }
        
    r = await async_client.post("/productivity/reminders/create", json=payload)
        
    assert r.status_code == 200
    assert r.json()["created"] == 1
        
    # Verify defaults were applied
    assert emitted[0]["payload"]["due_at"] is None
    assert emitted[0]["payload"]["source"] == "mailbox"
    assert emitted[0]["rationale"] == "bill/event reminder"

@pytest.mark.asyncio
async def test_calendar_event_empty_list(async_client):
    """
    Test that empty events list returns error.
    """
    payload = {"items": []}
        
    r = await async_client.post("/productivity/calendar/create", json=payload)
        
    assert r.status_code == 400
    assert "No events" in r.json()["detail"]

@pytest.mark.asyncio
async def test_list_reminders_empty(monkeypatch, async_client):
    """
    Test listing reminders when none exist.
    """
    # Mock ES to return empty results
    class FakeES:
        def search(self, index, body):
            return {
                "hits": {
                    "hits": [],
                    "total": {"value": 0}
                }
            }
    
    import app.logic.search as S
    monkeypatch.setattr(S, "es_client", lambda: FakeES())

    r = await async_client.get("/productivity/reminders/list")
        
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 0

@pytest.mark.asyncio
async def test_list_reminders_with_data(monkeypatch, async_client):
    """
    Test listing reminders with actual data.
    """
    # Mock ES to return fake reminders
    class FakeES:
        def search(self, index, body):
            return {
                "hits": {
                    "hits": [
                        {
                            "_source": {
                                "action": "create_reminder",
                                "created_at": "2025-10-10T12:00:00Z",
                                "payload": {
                                    "email_id": "bill_1",
                                    "title": "Pay electric bill",
                                    "due_at": "2025-10-15T17:00:00Z",
                                    "notes": "Due on 15th"
                                }
                            }
                        }
                    ],
                    "total": {"value": 1}
                }
            }
    
    import app.logic.search as S
    monkeypatch.setattr(S, "es_client", lambda: FakeES())

    r = await async_client.get("/productivity/reminders/list?limit=10")
        
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["email_id"] == "bill_1"
    assert data["items"][0]["title"] == "Pay electric bill"

@pytest.mark.asyncio
async def test_reminder_with_custom_source(monkeypatch, async_client):
    """
    Test creating reminder with custom source.
    """
    emitted = []
    monkeypatch.setattr(AUD, "emit_audit", lambda doc: emitted.append(doc))

    payload = {
        "items": [
            {
                "email_id": "task_1",
                "title": "Review PR",
                "source": "github",
                "notes": "From GitHub notification"
            }
        ]
    }
        
    r = await async_client.post("/productivity/reminders/create", json=payload)
        
    assert r.status_code == 200
    assert emitted[0]["payload"]["source"] == "github"
    assert emitted[0]["rationale"] == "From GitHub notification"
