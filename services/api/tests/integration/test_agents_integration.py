"""
Integration tests for Agents with real Elasticsearch.

These tests require:
- PostgreSQL (for audit logs)
- Elasticsearch (for warehouse health checks)

Run with: pytest -v tests/integration/test_agents_integration.py -m integration
"""

import os
from datetime import datetime, timezone

import pytest
from elasticsearch import Elasticsearch

from app.agents.executor import AgentExecutor
from app.agents.warehouse import WarehouseHealthAgent
from app.services.agent_auditor import AgentAuditor
from app.services.provider_factory import ProviderFactory


# ============================================================================
# SETUP & FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def es_client():
    """Real Elasticsearch client for integration tests."""
    if os.getenv("ES_ENABLED", "false").lower() != "true":
        pytest.skip("Elasticsearch not enabled (set ES_ENABLED=true)")

    host = os.getenv("ES_HOST", "localhost")
    port = int(os.getenv("ES_PORT", "9200"))
    
    client = Elasticsearch([f"http://{host}:{port}"])
    
    # Verify connection
    if not client.ping():
        pytest.skip("Elasticsearch not reachable")
    
    return client


@pytest.fixture(scope="module")
def test_index(es_client):
    """Create a test index with sample data."""
    index_name = "test-emails-integration"
    
    # Delete if exists
    if es_client.indices.exists(index=index_name):
        es_client.indices.delete(index=index_name)
    
    # Create index
    es_client.indices.create(
        index=index_name,
        body={
            "mappings": {
                "properties": {
                    "received_at": {"type": "date"},
                    "subject": {"type": "text"},
                    "sender": {"type": "keyword"},
                }
            }
        },
    )
    
    # Insert sample documents (simulate 7 days of emails)
    base_date = datetime.now(timezone.utc)
    for day_offset in range(7):
        for i in range(10):  # 10 emails per day
            doc_date = base_date.replace(
                hour=0, minute=0, second=0, microsecond=0
            ).timestamp() - (day_offset * 86400)
            
            es_client.index(
                index=index_name,
                document={
                    "received_at": datetime.fromtimestamp(doc_date, tz=timezone.utc).isoformat(),
                    "subject": f"Test email {i} from day {day_offset}",
                    "sender": f"sender{i}@test.com",
                },
            )
    
    # Refresh to make documents searchable
    es_client.indices.refresh(index=index_name)
    
    yield index_name
    
    # Cleanup
    es_client.indices.delete(index=index_name)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.integration
class TestWarehouseAgentWithRealES:
    """Test Warehouse Health Agent with real Elasticsearch."""

    def test_warehouse_agent_queries_real_es(self, test_index, db_session):
        """Warehouse agent should query real ES and return actual counts."""
        # Arrange
        plan = {
            "objective": "Check warehouse health",
            "dry_run": True,
            "allow_actions": False,
            "steps": WarehouseHealthAgent.plan({"dry_run": True})["steps"],
            "config": {
                "es": {"index": test_index},
                "bq": {"dataset": "analytics", "table": "emails"},
                "dbt": {"target": "dev", "models": ["tag:daily"]},
            },
        }
        
        # Act
        result = WarehouseHealthAgent.execute(plan)
        
        # Assert - Should have real ES data
        assert "parity" in result
        assert result["parity"]["es_count"] == 70  # 7 days * 10 emails
        assert result["parity"]["status"] in ["ok", "degraded"]
        
        # Should have daily breakdown
        assert "daily_breakdown" in result["parity"]
        assert len(result["parity"]["daily_breakdown"]) == 7

    def test_warehouse_agent_freshness_check(self, test_index, db_session):
        """Warehouse agent should check data freshness from real ES."""
        # Arrange
        plan = {
            "objective": "Check data freshness",
            "dry_run": True,
            "allow_actions": False,
            "steps": WarehouseHealthAgent.plan({"dry_run": True})["steps"],
            "config": {
                "es": {"index": test_index},
                "bq": {"dataset": "analytics", "table": "emails"},
                "dbt": {"target": "dev", "models": ["tag:daily"]},
            },
        }
        
        # Act
        result = WarehouseHealthAgent.execute(plan)
        
        # Assert - Should have freshness data
        assert "freshness" in result
        assert result["freshness"]["latest_event_ts"] is not None
        assert result["freshness"]["age_minutes"] is not None
        assert isinstance(result["freshness"]["within_slo"], bool)

    def test_warehouse_agent_with_executor_and_audit(self, test_index, db_session):
        """Full integration: Executor + Agent + Real ES + Audit."""
        # Arrange
        auditor = AgentAuditor(db_session)
        executor = AgentExecutor(run_store={}, auditor=auditor, event_bus=None)
        
        request = {
            "objective": "Monitor warehouse health",
            "dry_run": True,
            "allow_actions": False,
        }
        
        # Override config to use test index
        plan = WarehouseHealthAgent.plan(request)
        plan["config"] = {
            "es": {"index": test_index},
            "bq": {"dataset": "analytics", "table": "emails"},
            "dbt": {"target": "dev", "models": ["tag:daily"]},
        }
        
        # Act
        run_id = executor.execute(
            plan=plan,
            handler=WarehouseHealthAgent,
            user_email="integration-test@applylens.com",
            event_bus_enabled=False,
        )
        
        # Assert - Should complete successfully
        assert run_id is not None
        assert run_id in executor.run_store
        
        run_result = executor.run_store[run_id]
        assert run_result["status"] == "success"
        assert "parity" in run_result["artifacts"]
        assert run_result["artifacts"]["parity"]["es_count"] == 70


@pytest.mark.integration
class TestProviderFactoryIntegration:
    """Test ProviderFactory with real Elasticsearch."""

    def test_es_provider_aggregate_daily(self, test_index, es_client):
        """ES provider should aggregate daily counts from real index."""
        # Arrange
        factory = ProviderFactory()
        es_provider = factory.es()
        
        # Act
        result = es_provider.aggregate_daily(index=test_index, days=7)
        
        # Assert
        assert len(result) == 7
        for day_data in result:
            assert "date" in day_data
            assert "emails" in day_data
            assert day_data["emails"] == 10  # 10 emails per day

    def test_es_provider_latest_event_ts(self, test_index, es_client):
        """ES provider should fetch latest event timestamp."""
        # Arrange
        factory = ProviderFactory()
        es_provider = factory.es()
        
        # Act
        latest_ts = es_provider.latest_event_ts(index=test_index)
        
        # Assert
        assert latest_ts is not None
        assert isinstance(latest_ts, str)
        # Should be ISO format timestamp
        datetime.fromisoformat(latest_ts.replace("Z", "+00:00"))

    def test_es_provider_count(self, test_index, es_client):
        """ES provider should count documents in real index."""
        # Arrange
        factory = ProviderFactory()
        es_provider = factory.es()
        
        # Act
        count = es_provider.count(index=test_index)
        
        # Assert
        assert count == 70  # 7 days * 10 emails
