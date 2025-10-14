"""
E2E tests for validate_backfill.py script with mocked Elasticsearch.

Tests validation logic without requiring a real ES cluster.
"""

import json
import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import validate_backfill as V  # noqa: E402


class FakeES:
    """Mock Elasticsearch client that returns pre-configured counts."""

    def __init__(self, counts):
        """
        Initialize with count mappings.

        Args:
            counts: Dict mapping query signature tuples to count values
        """
        self._counts = counts

    def count(self, index, body):
        """Mock count() method that returns counts based on query signature."""
        query = body.get("query", {})

        # Create a signature based on query structure
        sig_parts = []
        bool_query = query.get("bool", {})

        # Check for category filter
        for filter_item in bool_query.get("filter", []):
            if filter_item.get("term", {}).get("category") == "bills":
                sig_parts.append("term:category=bills")
            if filter_item.get("exists", {}).get("field") == "dates":
                sig_parts.append("exists:dates")
            if filter_item.get("exists", {}).get("field") == "expires_at":
                sig_parts.append("exists:expires_at")

        # Check for must_not (missing dates)
        for must_not_item in bool_query.get("must_not", []):
            if must_not_item.get("exists", {}).get("field") == "dates":
                sig_parts.append("must_not:dates")

        sig = tuple(sorted(sig_parts))
        return {"count": self._counts.get(sig, 0)}


def test_validate_backfill_happy_path(monkeypatch, capsys):
    """Test validation with some missing dates and partial expires_at coverage."""
    # Setup scenario:
    # - 3 bills missing dates
    # - 20 bills with dates
    # - 18 bills with expires_at
    counts = {
        ("must_not:dates", "term:category=bills"): 3,
        ("exists:dates", "term:category=bills"): 20,
        ("exists:dates", "exists:expires_at", "term:category=bills"): 18,
    }

    monkeypatch.setattr(V, "es", lambda: FakeES(counts))
    monkeypatch.setenv("ES_EMAIL_INDEX", "gmail_emails_v2")

    # Parse args for --pretty
    monkeypatch.setattr(sys, "argv", ["validate_backfill.py", "--pretty"])

    V.main()

    out = capsys.readouterr().out
    assert "Missing dates[] (bills): 3" in out
    assert "Bills with dates[]:      20" in out
    assert "Bills with expires_at:   18" in out
    assert "Verdict: CHECK" in out  # CHECK because missing > 0


def test_validate_backfill_json_ok(monkeypatch, capsys):
    """Test validation with perfect backfill (no missing dates, all have expires_at)."""
    # Perfect scenario:
    # - 0 bills missing dates
    # - 10 bills with dates
    # - 10 bills with expires_at (100% coverage)
    counts = {
        ("must_not:dates", "term:category=bills"): 0,
        ("exists:dates", "term:category=bills"): 10,
        ("exists:dates", "exists:expires_at", "term:category=bills"): 10,
    }

    monkeypatch.setattr(V, "es", lambda: FakeES(counts))
    monkeypatch.setenv("ES_EMAIL_INDEX", "gmail_emails_v2")

    # Parse args for --json
    monkeypatch.setattr(sys, "argv", ["validate_backfill.py", "--json"])

    V.main()

    out = capsys.readouterr().out
    result = json.loads(out)

    assert result["index"] == "gmail_emails_v2"
    assert result["missing_dates_count"] == 0
    assert result["bills_with_dates"] == 10
    assert result["bills_with_expires_at"] == 10
    assert result["verdict"] == "OK"
    assert "timestamp" in result


def test_count_functions_directly(monkeypatch):
    """Test count functions directly without main()."""
    counts = {
        ("must_not:dates", "term:category=bills"): 5,
        ("exists:dates", "term:category=bills"): 100,
        ("exists:dates", "exists:expires_at", "term:category=bills"): 95,
    }

    monkeypatch.setattr(V, "es", lambda: FakeES(counts))
    monkeypatch.setenv("ES_EMAIL_INDEX", "test_index")

    client = V.es()

    # Test count_missing_dates
    missing = V.count_missing_dates(client)
    assert missing == 5

    # Test counts_with_expiry
    total, with_exp = V.counts_with_expiry(client)
    assert total == 100
    assert with_exp == 95


def test_validate_backfill_check_verdict(monkeypatch, capsys):
    """Test that verdict is CHECK when there are anomalies."""
    # Anomaly: more bills with expires_at than with dates (shouldn't happen)
    counts = {
        ("must_not:dates", "term:category=bills"): 0,
        ("exists:dates", "term:category=bills"): 10,
        ("exists:dates", "exists:expires_at", "term:category=bills"): 15,  # Anomaly!
    }

    monkeypatch.setattr(V, "es", lambda: FakeES(counts))
    monkeypatch.setenv("ES_EMAIL_INDEX", "gmail_emails_v2")
    monkeypatch.setattr(sys, "argv", ["validate_backfill.py", "--json"])

    V.main()

    out = capsys.readouterr().out
    result = json.loads(out)

    assert result["verdict"] == "CHECK"  # Should flag the anomaly
