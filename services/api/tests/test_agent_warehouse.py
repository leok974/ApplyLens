"""Golden tests for Warehouse Health Agent.

Tests the full agent execution with deterministic mock data.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_warehouse_agent_list():
    """Test that warehouse.health agent is registered."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/agents")
        
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "warehouse.health" in data["agents"]


@pytest.mark.asyncio
async def test_warehouse_agent_run():
    """Test warehouse health agent execution."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post(
            "/agents/warehouse.health/run",
            json={
                "objective": "daily parity check",
                "dry_run": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check run metadata
        assert data["status"] in ("running", "succeeded", "failed", "queued")
        assert "run_id" in data
        assert "started_at" in data
        assert "logs" in data
        
        # Check artifacts
        artifacts = data["artifacts"]
        assert "parity_ok" in artifacts
        assert artifacts["parity_ok"] is True
        
        # Check ES results
        assert "es_hits_count" in artifacts
        assert "es_sample" in artifacts
        assert isinstance(artifacts["es_sample"], list)
        
        # Check BQ results
        assert "bq_rows_count" in artifacts
        assert "bq_rows" in artifacts
        assert "bq_stats" in artifacts
        
        # Check dbt results
        assert "dbt" in artifacts
        dbt_result = artifacts["dbt"]
        assert "success" in dbt_result
        assert "elapsed_sec" in dbt_result
        
        # Check summary
        assert "summary" in artifacts
        summary = artifacts["summary"]
        assert "status" in summary
        assert summary["status"] in ("healthy", "degraded")
        assert "checks_passed" in summary
        assert "total_checks" in summary


@pytest.mark.asyncio
async def test_warehouse_agent_runs_list():
    """Test listing runs for warehouse agent."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # First, run the agent
        await client.post(
            "/agents/warehouse.health/run",
            json={"objective": "test run", "dry_run": True}
        )
        
        # Then list runs
        response = await client.get("/agents/warehouse.health/runs")
        
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data
        assert len(data["runs"]) > 0


@pytest.mark.asyncio
async def test_warehouse_agent_golden_output():
    """Golden test: verify exact structure and content."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post(
            "/agents/warehouse.health/run",
            json={
                "objective": "golden test",
                "dry_run": True
            }
        )
        
        data = response.json()
        artifacts = data["artifacts"]
        
        # Verify deterministic mock data
        
        # ES should return 2 emails (from mock)
        assert artifacts["es_hits_count"] == 2
        assert len(artifacts["es_sample"]) <= 3
        
        # BQ should return 2 rows (from mock)
        assert artifacts["bq_rows_count"] == 2
        assert artifacts["bq_rows"][0]["day"] == "2025-10-15"
        assert artifacts["bq_rows"][0]["emails"] == 42
        
        # dbt should succeed
        assert artifacts["dbt"]["success"] is True
        assert artifacts["dbt"]["artifacts_path"] == "target/run_results.json"
        
        # Summary should show healthy
        assert artifacts["summary"]["status"] == "healthy"
        assert artifacts["summary"]["total_checks"] == 4


@pytest.mark.asyncio
async def test_unknown_agent():
    """Test running unknown agent returns 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post(
            "/agents/unknown.agent/run",
            json={"objective": "test", "dry_run": True}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
