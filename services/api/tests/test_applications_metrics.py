"""Test metrics for application creation from email threads."""

import httpx
from prometheus_client import REGISTRY


async def test_applications_from_thread_metric_increments(
    async_client: httpx.AsyncClient,
):
    """Test that the metric increments when an application is created from a thread."""
    # Get initial metric value
    before = 0
    for metric in REGISTRY.collect():
        if metric.name == "applylens_applications_created_from_thread_total":
            for sample in metric.samples:
                if sample.name == "applylens_applications_created_from_thread_total":
                    before = sample.value
                    break

    # Create an application from a thread
    # Use X-API-Key header to bypass CSRF protection in tests
    response = await async_client.post(
        "/applications/backfill-from-email",
        json={
            "gmail_thread_id": "test-thread-123",
            "company": "TestCorp",
            "role": "Engineer",
            "source": "Email",
        },
        headers={"X-API-Key": "test-key"},
    )

    # Should succeed
    if response.status_code != 200:
        print(f"ERROR: {response.status_code} - {response.text}")
    assert response.status_code == 200
    data = response.json()
    assert data["saved"]["company"] == "TestCorp"
    assert data["saved"]["role"] == "Engineer"

    # Get metric value after creation
    after = 0
    for metric in REGISTRY.collect():
        if metric.name == "applylens_applications_created_from_thread_total":
            for sample in metric.samples:
                if sample.name == "applylens_applications_created_from_thread_total":
                    after = sample.value
                    break

    # Metric should have incremented by exactly 1
    assert after == before + 1


async def test_applications_from_thread_metric_in_prometheus_export(
    async_client: httpx.AsyncClient,
):
    """Test that the metric appears in the /metrics endpoint."""
    # First create an application to ensure the metric exists
    await async_client.post(
        "/applications/backfill-from-email",
        json={
            "gmail_thread_id": "test-thread-456",
            "company": "AnotherCorp",
            "role": "Developer",
        },
        headers={"X-API-Key": "test-key"},
    )

    # Fetch metrics endpoint
    response = await async_client.get("/metrics")
    assert response.status_code == 200

    # Check that our metric appears in the output
    metrics_text = response.text
    assert "applylens_applications_created_from_thread_total" in metrics_text

    # Verify it's a counter (should have _total suffix and TYPE counter)
    lines = metrics_text.split("\n")
    metric_lines = [
        line for line in lines if "applylens_applications_created_from_thread" in line
    ]

    # Should have at least TYPE and value lines
    assert len(metric_lines) >= 2

    # Check for TYPE declaration
    type_line = next(
        (
            line
            for line in metric_lines
            if line.startswith("# TYPE applylens_applications_created_from_thread")
        ),
        None,
    )
    assert type_line is not None
    assert "counter" in type_line.lower()


async def test_applications_from_thread_metric_only_on_success(
    async_client: httpx.AsyncClient,
):
    """Test that metric only increments on successful application creation."""
    # Get initial metric value
    before = 0
    for metric in REGISTRY.collect():
        if metric.name == "applylens_applications_created_from_thread_total":
            for sample in metric.samples:
                if sample.name == "applylens_applications_created_from_thread_total":
                    before = sample.value
                    break

    # Try to create application - backfill-from-email requires at least company or role
    # With only thread_id, it should fail validation (422)
    response = await async_client.post(
        "/applications/backfill-from-email",
        json={
            "gmail_thread_id": "invalid-thread",
            # No company or role - should fail
        },
        headers={"X-API-Key": "test-key"},
    )

    # Should fail validation (requires company or role)
    assert response.status_code == 422

    # Get metric value after failed request
    after = 0
    for metric in REGISTRY.collect():
        if metric.name == "applylens_applications_created_from_thread_total":
            for sample in metric.samples:
                if sample.name == "applylens_applications_created_from_thread_total":
                    after = sample.value
                    break

    # Metric should NOT have incremented
    assert after == before
