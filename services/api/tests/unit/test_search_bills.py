"""
Unit tests for bill search functionality.

Tests Elasticsearch queries for finding bills due before a cutoff date.
Uses monkeypatching to mock ES client responses.
"""
import asyncio
import pytest
import app.logic.search as S


class FakeESClient:
    """Mock Elasticsearch client for testing."""
    
    def __init__(self, hits):
        """Initialize with list of hits to return."""
        self._hits = hits
    
    def search(self, index, body):
        """Return mocked search results."""
        return {"hits": {"hits": self._hits}}


def _hit(doc_id: str, src: dict) -> dict:
    """Helper to create ES hit structure."""
    return {"_id": doc_id, "_source": {"id": doc_id, **src}}


def test_find_bills_due_before_monkeypatched(monkeypatch):
    """Test finding bills with mocked ES response."""
    fake_hits = [
        _hit(
            "bill_1",
            {
                "category": "bills",
                "dates": ["2025-10-11T00:00:00Z"],
                "subject": "Electric Co bill due Oct 11",
                "sender_domain": "electric.example.com",
                "received_at": "2025-10-01T10:00:00Z",
                "money_amounts": [{"amount": 125.50, "currency": "USD"}],
            },
        ),
        _hit(
            "bill_2",
            {
                "category": "bills",
                "expires_at": "2025-10-09T00:00:00Z",
                "subject": "Water bill due Oct 9",
                "sender_domain": "water.example.com",
                "received_at": "2025-09-28T12:00:00Z",
                "money_amounts": [{"amount": 45.00, "currency": "USD"}],
            },
        ),
    ]
    
    # Monkeypatch ES client
    monkeypatch.setattr(S, "es_client", lambda: FakeESClient(fake_hits))
    
    # Execute search
    res = asyncio.get_event_loop().run_until_complete(
        S.find_bills_due_before("2025-10-12T00:00:00Z")
    )
    
    # Verify results
    ids = [r["id"] for r in res]
    assert "bill_1" in ids
    assert "bill_2" in ids
    assert len(res) == 2
    
    # Verify enriched fields
    bill1 = next(r for r in res if r["id"] == "bill_1")
    assert bill1["subject"] == "Electric Co bill due Oct 11"
    assert bill1["dates"] == ["2025-10-11T00:00:00Z"]
    assert bill1["money_amounts"] == [{"amount": 125.50, "currency": "USD"}]
    
    bill2 = next(r for r in res if r["id"] == "bill_2")
    assert bill2["expires_at"] == "2025-10-09T00:00:00Z"
    assert bill2["money_amounts"] == [{"amount": 45.00, "currency": "USD"}]


def test_find_bills_empty_results(monkeypatch):
    """Test finding bills when no results match."""
    # Empty hits
    monkeypatch.setattr(S, "es_client", lambda: FakeESClient([]))
    
    res = asyncio.get_event_loop().run_until_complete(
        S.find_bills_due_before("2025-10-12T00:00:00Z")
    )
    
    assert res == []


def test_find_bills_with_limit(monkeypatch):
    """Test that limit parameter is respected."""
    # Create many fake bills
    fake_hits = [
        _hit(
            f"bill_{i}",
            {
                "category": "bills",
                "dates": ["2025-10-10T00:00:00Z"],
                "subject": f"Bill {i}",
                "sender_domain": "sender.example.com",
                "received_at": "2025-10-01T10:00:00Z",
            },
        )
        for i in range(10)
    ]
    
    # Verify query body contains limit
    captured_body = {}
    
    class CaptureESClient(FakeESClient):
        def search(self, index, body):
            captured_body.update(body)
            return super().search(index, body)
    
    monkeypatch.setattr(S, "es_client", lambda: CaptureESClient(fake_hits[:5]))
    
    res = asyncio.get_event_loop().run_until_complete(
        S.find_bills_due_before("2025-10-12T00:00:00Z", limit=5)
    )
    
    assert captured_body["size"] == 5
    assert len(res) == 5


def test_find_bills_query_structure(monkeypatch):
    """Test that the ES query is structured correctly."""
    captured_body = {}
    
    class CaptureESClient(FakeESClient):
        def search(self, index, body):
            captured_body.update(body)
            return {"hits": {"hits": []}}
    
    monkeypatch.setattr(S, "es_client", lambda: CaptureESClient([]))
    
    asyncio.get_event_loop().run_until_complete(
        S.find_bills_due_before("2025-10-15T00:00:00Z")
    )
    
    # Verify query structure
    query = captured_body["query"]
    assert "bool" in query
    
    filters = query["bool"]["filter"]
    assert len(filters) == 2
    
    # First filter: category = bills
    assert {"term": {"category": "bills"}} in filters
    
    # Second filter: date range
    date_filter = next(f for f in filters if "bool" in f)
    should_clauses = date_filter["bool"]["should"]
    
    assert len(should_clauses) == 2
    assert {"range": {"dates": {"lt": "2025-10-15T00:00:00Z"}}} in should_clauses
    assert {"range": {"expires_at": {"lt": "2025-10-15T00:00:00Z"}}} in should_clauses
    assert date_filter["bool"]["minimum_should_match"] == 1
    
    # Verify source fields
    assert "id" in captured_body["_source"]
    assert "category" in captured_body["_source"]
    assert "subject" in captured_body["_source"]
    assert "money_amounts" in captured_body["_source"]
    assert "dates" in captured_body["_source"]
    assert "expires_at" in captured_body["_source"]


def test_find_bills_with_mixed_date_fields(monkeypatch):
    """Test bills with both dates array and expires_at."""
    fake_hits = [
        _hit(
            "bill_mixed",
            {
                "category": "bills",
                "dates": ["2025-10-15T00:00:00Z", "2025-10-20T00:00:00Z"],
                "expires_at": "2025-10-14T00:00:00Z",  # Earlier than dates
                "subject": "Bill with multiple dates",
                "sender_domain": "sender.example.com",
                "received_at": "2025-10-01T10:00:00Z",
                "money_amounts": [],
            },
        ),
    ]
    
    monkeypatch.setattr(S, "es_client", lambda: FakeESClient(fake_hits))
    
    res = asyncio.get_event_loop().run_until_complete(
        S.find_bills_due_before("2025-10-16T00:00:00Z")
    )
    
    assert len(res) == 1
    bill = res[0]
    assert bill["dates"] == ["2025-10-15T00:00:00Z", "2025-10-20T00:00:00Z"]
    assert bill["expires_at"] == "2025-10-14T00:00:00Z"


def test_find_bills_missing_optional_fields(monkeypatch):
    """Test bills with missing optional fields like money_amounts or dates."""
    fake_hits = [
        _hit(
            "bill_minimal",
            {
                "category": "bills",
                "expires_at": "2025-10-10T00:00:00Z",
                "subject": "Minimal bill",
                "sender_domain": "sender.example.com",
                "received_at": "2025-10-01T10:00:00Z",
                # No dates or money_amounts
            },
        ),
    ]
    
    monkeypatch.setattr(S, "es_client", lambda: FakeESClient(fake_hits))
    
    res = asyncio.get_event_loop().run_until_complete(
        S.find_bills_due_before("2025-10-12T00:00:00Z")
    )
    
    assert len(res) == 1
    bill = res[0]
    assert bill["money_amounts"] == []
    assert bill["dates"] == []
    assert bill["expires_at"] == "2025-10-10T00:00:00Z"


@pytest.mark.asyncio
async def test_find_bills_async_api():
    """Test that function is properly async (can be awaited)."""
    # This test just verifies the async signature works
    # In real tests, we'd monkeypatch the ES client
    # Here we just verify the function can be awaited
    import inspect
    assert inspect.iscoroutinefunction(S.find_bills_due_before)
