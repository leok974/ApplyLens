"""
Tests for metrics summary endpoint.

Validates the /metrics/summary endpoint that provides:
- Scan runs count (last 7 days)
- Applications created from threads total
"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_metrics_summary_endpoint_shape(async_client: httpx.AsyncClient):
    """Verify /metrics/summary returns expected structure."""
    response = await async_client.get("/metrics/summary")

    assert response.status_code == 200
    data = response.json()

    # Verify required fields exist
    assert "scan_runs_last_7_days" in data
    assert "applications_created_from_threads_total" in data
    assert "generated_at" in data

    # Verify types
    assert isinstance(data["scan_runs_last_7_days"], int)
    assert isinstance(data["applications_created_from_threads_total"], int)
    assert isinstance(data["generated_at"], str)

    # Verify non-negative counts
    assert data["scan_runs_last_7_days"] >= 0
    assert data["applications_created_from_threads_total"] >= 0


@pytest.mark.asyncio
async def test_metrics_summary_returns_valid_iso_timestamp(
    async_client: httpx.AsyncClient,
):
    """Verify generated_at is a valid ISO 8601 timestamp."""
    from datetime import datetime

    response = await async_client.get("/metrics/summary")
    assert response.status_code == 200

    data = response.json()
    timestamp_str = data["generated_at"]

    # Should parse without error
    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    assert timestamp is not None


@pytest.mark.asyncio
async def test_metrics_summary_accessible_without_auth(async_client: httpx.AsyncClient):
    """Verify endpoint is accessible (for internal monitoring)."""
    # Note: In production, this should be protected or only accessible internally
    # For now, testing that it returns data without authentication
    response = await async_client.get("/metrics/summary")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_metrics_summary_idempotent(async_client: httpx.AsyncClient):
    """Verify multiple calls return consistent structure."""
    response1 = await async_client.get("/metrics/summary")
    response2 = await async_client.get("/metrics/summary")

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    # Structure should be identical
    assert set(data1.keys()) == set(data2.keys())

    # Values should be the same (or very close for counts)
    # Allow for potential race conditions in count increments
    assert (
        data1["applications_created_from_threads_total"]
        == data2["applications_created_from_threads_total"]
    )


@pytest.mark.skipif(
    True,
    reason="Integration test - requires database with AgentAuditLog table",
)
@pytest.mark.asyncio
async def test_metrics_summary_with_agent_runs(
    async_client: httpx.AsyncClient, db_session
):
    """Verify scan_runs_last_7_days counts recent agent runs correctly."""
    from datetime import datetime, timedelta
    from app.models import AgentAuditLog

    # Create test agent runs
    now = datetime.utcnow()
    for i in range(5):
        log = AgentAuditLog(
            run_id=f"test_run_{i}",
            agent="mailbox_assistant",
            objective="test scan",
            status="succeeded",
            started_at=now - timedelta(days=i),
        )
        db_session.add(log)
    db_session.commit()

    response = await async_client.get("/metrics/summary")
    assert response.status_code == 200

    data = response.json()
    # Should count the 5 runs within last 7 days
    assert data["scan_runs_last_7_days"] >= 5


@pytest.mark.skipif(
    True,
    reason="Integration test - requires Prometheus metrics",
)
@pytest.mark.asyncio
async def test_metrics_summary_with_application_metric(async_client: httpx.AsyncClient):
    """Verify applications_created_from_threads_total reflects counter value."""
    from app.core.metrics import applications_created_from_thread_total

    # Increment the counter
    applications_created_from_thread_total.inc(3)

    response = await async_client.get("/metrics/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["applications_created_from_threads_total"] >= 3
