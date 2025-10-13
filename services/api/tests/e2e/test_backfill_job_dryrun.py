"""
E2E test for backfill_bill_dates.py script.

Tests the control flow without requiring a real Elasticsearch cluster
by mocking the ES client and helpers.
"""
import os
import sys
import pytest

# Add scripts to path
scripts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

import backfill_bill_dates as job  # noqa: E402


class FakeScan:
    """Mock elasticsearch.helpers.scan iterator."""
    
    def __iter__(self):
        # Bill with date in body
        yield {
            "_id": "bill_001",
            "_source": {
                "subject": "Your Bill",
                "body_text": "Amount due by 10/15/2025. Please pay promptly.",
                "received_at": "2025-10-01T00:00:00Z",
                "category": "bills"
            }
        }
        
        # Bill with wrong expires_at (should be corrected)
        yield {
            "_id": "bill_002",
            "_source": {
                "subject": "Payment Reminder",
                "body_text": "Pay by Oct 20, 2025",
                "received_at": "2025-10-01T00:00:00Z",
                "category": "bills",
                "dates": ["2025-10-20T00:00:00Z"],
                "expires_at": "2025-10-25T00:00:00Z"  # Wrong - should be 10/20
            }
        }
        
        # Bill with earlier existing date (should keep earlier expires_at)
        yield {
            "_id": "bill_003",
            "_source": {
                "subject": "Bill Statement",
                "body_text": "Payment due 10/25/2025",
                "received_at": "2025-10-01T00:00:00Z",
                "category": "bills",
                "dates": ["2025-10-18T00:00:00Z"],
                "expires_at": "2025-10-10T00:00:00Z"  # Earlier than extracted
            }
        }
        
        # Bill with no dates extractable
        yield {
            "_id": "bill_004",
            "_source": {
                "subject": "Monthly Statement",
                "body_text": "Thank you for your business.",
                "received_at": "2025-10-01T00:00:00Z",
                "category": "bills"
            }
        }


class FakeESClient:
    """Mock Elasticsearch client."""
    
    def __init__(self):
        self.bulk_calls = []
    
    def bulk(self, actions):
        """Mock bulk update - just record the calls."""
        self.bulk_calls.append(list(actions))


def fake_es():
    """Factory function to create fake ES client."""
    return FakeESClient()


def fake_scan(client, **kwargs):
    """Mock elasticsearch.helpers.scan."""
    return FakeScan()


def fake_bulk(client, actions):
    """Mock elasticsearch.helpers.bulk."""
    action_list = list(actions)
    client.bulk_calls.append(action_list)
    return (len(action_list), [])


def test_backfill_dry_run_monkeypatched(monkeypatch, capsys):
    """Test backfill in dry run mode with mocked ES."""
    # Patch the functions
    monkeypatch.setattr(job, "es", fake_es)
    monkeypatch.setattr(job.helpers, "scan", fake_scan)
    monkeypatch.setattr(job.helpers, "bulk", fake_bulk)
    
    # Set dry run mode
    monkeypatch.setenv("DRY_RUN", "1")
    monkeypatch.setenv("ES_EMAIL_INDEX", "test_index")
    monkeypatch.setenv("BATCH", "100")
    
    # Run the backfill
    job.run()
    
    # Check output
    captured = capsys.readouterr()
    output = captured.out
    
    # Should indicate dry run mode
    assert "DRY RUN" in output or "dry-run" in output.lower()
    assert "completed" in output.lower()
    
    # Should show scanned bills
    assert "Scanned:" in output
    
    # Should show some would-be updates (bill_001 and bill_002 should update)
    # bill_003 keeps earlier expires_at, bill_004 has no dates
    assert "Updated:" in output or "updated" in output.lower()


def test_backfill_live_mode_records_updates(monkeypatch, capsys):
    """Test backfill in live mode records bulk updates."""
    # Create fake client
    fake_client = FakeESClient()
    
    # Patch functions
    monkeypatch.setattr(job, "es", lambda: fake_client)
    monkeypatch.setattr(job.helpers, "scan", fake_scan)
    monkeypatch.setattr(job.helpers, "bulk", fake_bulk)
    
    # Set live mode
    monkeypatch.setenv("DRY_RUN", "0")
    monkeypatch.setenv("ES_EMAIL_INDEX", "test_index")
    monkeypatch.setenv("BATCH", "100")
    
    # Run the backfill
    job.run()
    
    # Check output
    captured = capsys.readouterr()
    output = captured.out
    
    # Should NOT be dry run
    assert "LIVE UPDATE" in output or ("DRY RUN" not in output and "dry-run" not in output.lower())
    assert "completed" in output.lower()
    
    # Should have called bulk at least once
    assert len(fake_client.bulk_calls) > 0, "Expected bulk updates to be called"
    
    # Check bulk calls contain updates
    all_actions = []
    for batch in fake_client.bulk_calls:
        all_actions.extend(batch)
    
    # Should have at least bill_001 and bill_002 updates
    assert len(all_actions) >= 2, f"Expected at least 2 updates, got {len(all_actions)}"
    
    # Verify action structure
    for action in all_actions:
        assert "_op_type" in action
        assert action["_op_type"] == "update"
        assert "_index" in action
        assert "_id" in action
        assert "doc" in action


def test_transform_logic_with_real_data():
    """Test the transform function with realistic bill data."""
    from backfill_bill_dates import transform
    
    # Test 1: Bill with extractable date
    doc1 = {
        "_id": "test_001",
        "_source": {
            "subject": "Electric Bill",
            "body_text": "Payment due by 11/15/2025",
            "received_at": "2025-10-10T12:00:00Z"
        }
    }
    result1 = transform(doc1)
    assert result1 is not None
    assert "dates" in result1
    assert any("2025-11-15" in d for d in result1["dates"])
    assert "expires_at" in result1
    assert result1["expires_at"].startswith("2025-11-15")
    
    # Test 2: Bill with no extractable dates
    doc2 = {
        "_id": "test_002",
        "_source": {
            "subject": "Monthly Statement",
            "body_text": "Thank you for your payment.",
            "received_at": "2025-10-10T12:00:00Z"
        }
    }
    result2 = transform(doc2)
    assert result2 is None  # No changes needed
    
    # Test 3: Bill with earlier existing expires_at
    doc3 = {
        "_id": "test_003",
        "_source": {
            "subject": "Reminder",
            "body_text": "Due on 10/20/2025",
            "received_at": "2025-10-10T12:00:00Z",
            "dates": ["2025-10-20T00:00:00Z"],
            "expires_at": "2025-10-15T00:00:00Z"  # Earlier
        }
    }
    result3 = transform(doc3)
    # Should keep earlier expires_at
    if result3:
        assert result3["expires_at"] == "2025-10-15T00:00:00Z"


def test_earliest_helper():
    """Test the earliest() helper function."""
    from backfill_bill_dates import earliest
    
    assert earliest([]) is None
    assert earliest(["2025-10-15T00:00:00Z"]) == "2025-10-15T00:00:00Z"
    assert earliest([
        "2025-10-20T00:00:00Z",
        "2025-10-15T00:00:00Z",
        "2025-10-25T00:00:00Z"
    ]) == "2025-10-15T00:00:00Z"
    assert earliest([None, "2025-10-15T00:00:00Z", None]) == "2025-10-15T00:00:00Z"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
