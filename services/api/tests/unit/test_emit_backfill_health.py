"""
Unit tests for emit_backfill_health.py script.

Tests the health emission logic with a mocked Elasticsearch client.
"""

import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import emit_backfill_health as E
import validate_backfill as V


class FakeES:
    """Mock Elasticsearch client that records index operations."""
    
    def __init__(self):
        """Initialize with empty tracking."""
        self.last_doc = None
        self.indexed_docs = []
    
    def index(self, index, document):
        """Record the index operation."""
        self.last_doc = (index, document)
        self.indexed_docs.append((index, document))
    
    def count(self, index, body):
        """Return fixed count for all queries."""
        return {"count": 7}


def test_emit_backfill_health_monkeypatched(monkeypatch):
    """
    Test that emit_backfill_health correctly indexes health data.
    
    Uses a mocked ES client that returns count=7 for all queries,
    so we expect: missing=7, with_dates=7, with_expires_at=7
    """
    fake_es = FakeES()
    
    # Patch both V and E since E imports from V
    monkeypatch.setattr(V, "es", lambda: fake_es)
    monkeypatch.setattr(E, "es", lambda: fake_es)
    
    # Run the health emission
    E.main()
    
    # Verify a document was indexed
    assert fake_es.last_doc is not None
    
    idx, doc = fake_es.last_doc
    
    # Check index name
    assert idx == "backfill_health_v1"
    
    # Check document structure
    required_fields = {"missing", "with_dates", "with_expires_at", "ts", "index"}
    assert required_fields <= set(doc.keys()), f"Missing fields: {required_fields - set(doc.keys())}"
    
    # Check values (FakeES returns 7 for all counts)
    assert doc["missing"] == 7
    assert doc["with_dates"] == 7
    assert doc["with_expires_at"] == 7
    
    # Check index name in document
    assert doc["index"] == "gmail_emails_v2"
    
    # Check timestamp format (ISO 8601 with Z suffix)
    assert "T" in doc["ts"]
    assert doc["ts"].endswith("Z")


def test_emit_backfill_health_custom_index(monkeypatch):
    """
    Test health emission with custom index names.
    
    Verifies that environment variables are respected.
    """
    fake_es = FakeES()
    monkeypatch.setattr(V, "es", lambda: fake_es)
    monkeypatch.setenv("ES_EMAIL_INDEX", "custom_emails")
    monkeypatch.setenv("ES_HEALTH_INDEX", "custom_health")
    
    # Need to reload the module to pick up new env vars
    import importlib
    importlib.reload(E)
    
    E.main()
    
    idx, doc = fake_es.last_doc
    
    # Check that custom health index was used
    assert idx == "custom_health"
    
    # Check that email index name appears in document
    assert doc["index"] == "custom_emails"


def test_emit_backfill_health_realistic_counts(monkeypatch):
    """
    Test with realistic count values that differ per query.
    
    Scenario:
    - 5 bills missing dates
    - 100 bills with dates
    - 95 bills with expires_at
    """
    class RealisticES:
        """ES client that returns different counts based on query."""
        def __init__(self):
            self.last_doc = None
        
        def index(self, index, document):
            self.last_doc = (index, document)
        
        def count(self, index, body):
            """Return counts based on query structure."""
            query = body["query"]
            bool_query = query.get("bool", {})
            filters = bool_query.get("filter", [])
            must_not = bool_query.get("must_not", [])
            
            # Detect query type
            has_dates = {"exists": {"field": "dates"}} in filters
            has_exp = {"exists": {"field": "expires_at"}} in filters
            missing = {"exists": {"field": "dates"}} in must_not
            
            if missing:
                return {"count": 5}  # 5 missing
            elif has_dates and has_exp:
                return {"count": 95}  # 95 with expires_at
            elif has_dates:
                return {"count": 100}  # 100 with dates
            
            return {"count": 0}
    
    realistic_es = RealisticES()
    
    # Patch both V and E
    monkeypatch.setattr(V, "es", lambda: realistic_es)
    monkeypatch.setattr(E, "es", lambda: realistic_es)
    
    E.main()
    
    idx, doc = realistic_es.last_doc
    
    # Verify realistic counts
    assert doc["missing"] == 5
    assert doc["with_dates"] == 100
    assert doc["with_expires_at"] == 95


def test_emit_backfill_health_multiple_calls(monkeypatch):
    """
    Test that multiple calls create multiple documents.
    
    Useful for verifying time-series behavior.
    """
    fake_es = FakeES()
    
    # Reset environment variables to defaults
    monkeypatch.setenv("ES_HEALTH_INDEX", "backfill_health_v1")
    monkeypatch.setenv("ES_EMAIL_INDEX", "gmail_emails_v2")
    
    # Patch both V and E
    monkeypatch.setattr(V, "es", lambda: fake_es)
    monkeypatch.setattr(E, "es", lambda: fake_es)
    
    # Need to reload E to pick up env vars
    import importlib
    importlib.reload(E)
    
    # Call health emission 3 times
    E.main()
    E.main()
    E.main()
    
    # Should have 3 documents indexed
    assert len(fake_es.indexed_docs) == 3
    
    # All should go to the same index
    indices = [idx for idx, _ in fake_es.indexed_docs]
    assert all(idx == "backfill_health_v1" for idx in indices)
    
    # All should have timestamps (different ones ideally, but at least present)
    timestamps = [doc["ts"] for _, doc in fake_es.indexed_docs]
    assert len(timestamps) == 3
    assert all("T" in ts for ts in timestamps)
