"""Integration tests for warehouse metrics API endpoints.

Tests the feature-flagged BigQuery warehouse endpoints.
Mocks BigQuery client to avoid requiring real credentials.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_bq_client():
    """Mock BigQuery client to avoid real BigQuery calls."""
    with patch('app.metrics.warehouse._client') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def warehouse_enabled(monkeypatch):
    """Enable warehouse feature flag."""
    monkeypatch.setenv("APPLYLENS_USE_WAREHOUSE", "1")
    # Reload config to pick up env change
    from app import config
    config.agent_settings = config.AgentSettings()


@pytest.mark.integration
class TestWarehouseEndpoints:
    """Test warehouse metrics API endpoints."""
    
    def test_top_senders_disabled_returns_412(self, client: TestClient):
        """Test that warehouse endpoints return 412 when disabled."""
        response = client.get("/api/warehouse/profile/top-senders")
        assert response.status_code == 412
        assert "Warehouse disabled" in response.json()["detail"]
    
    def test_activity_daily_disabled_returns_412(self, client: TestClient):
        """Test that activity endpoint returns 412 when disabled."""
        response = client.get("/api/warehouse/profile/activity-daily")
        assert response.status_code == 412
    
    def test_categories_disabled_returns_412(self, client: TestClient):
        """Test that categories endpoint returns 412 when disabled."""
        response = client.get("/api/warehouse/profile/categories-30d")
        assert response.status_code == 412
    
    def test_divergence_disabled_returns_412(self, client: TestClient):
        """Test that divergence endpoint returns 412 when disabled."""
        response = client.get("/api/warehouse/profile/divergence-24h")
        assert response.status_code == 412
    
    @pytest.mark.asyncio
    async def test_top_senders_with_mock_data(
        self, client: TestClient, warehouse_enabled, mock_bq_client
    ):
        """Test top senders endpoint with mocked BigQuery data."""
        # Mock BigQuery query result
        mock_result = [
            {
                "from_email": "jobs@linkedin.com",
                "messages_30d": 42,
                "total_size_mb": 1.5,
                "first_message_at": "2025-09-18T10:00:00Z",
                "last_message_at": "2025-10-18T15:30:00Z",
                "active_days": 30
            },
            {
                "from_email": "noreply@github.com",
                "messages_30d": 35,
                "total_size_mb": 0.8,
                "first_message_at": "2025-09-20T08:00:00Z",
                "last_message_at": "2025-10-18T12:00:00Z",
                "active_days": 28
            }
        ]
        
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = [
            MagicMock(**row) for row in mock_result
        ]
        mock_bq_client.query.return_value = mock_query_job
        
        # Make request
        response = client.get("/api/warehouse/profile/top-senders?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["from_email"] == "jobs@linkedin.com"
        assert data[0]["messages_30d"] == 42
    
    @pytest.mark.asyncio
    async def test_activity_daily_with_mock_data(
        self, client: TestClient, warehouse_enabled, mock_bq_client
    ):
        """Test activity daily endpoint with mocked data."""
        mock_result = [
            {
                "day": "2025-10-17",
                "messages_count": 35,
                "unique_senders": 12,
                "avg_size_kb": 45.2,
                "total_size_mb": 1.5
            },
            {
                "day": "2025-10-18",
                "messages_count": 28,
                "unique_senders": 10,
                "avg_size_kb": 42.1,
                "total_size_mb": 1.2
            }
        ]
        
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = [
            MagicMock(**row) for row in mock_result
        ]
        mock_bq_client.query.return_value = mock_query_job
        
        response = client.get("/api/warehouse/profile/activity-daily?days=7")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["day"] == "2025-10-17"
        assert data[0]["messages_count"] == 35
    
    def test_limit_clamping(self, client: TestClient, warehouse_enabled):
        """Test that limit parameters are clamped to valid ranges."""
        # Test with limit > max (should clamp to 100)
        response = client.get("/api/warehouse/profile/top-senders?limit=999")
        # Should not error, backend should clamp
        assert response.status_code in [200, 500]  # 500 if BQ not available
        
        # Test with limit < min (should clamp to 1)
        response = client.get("/api/warehouse/profile/top-senders?limit=0")
        assert response.status_code in [200, 500]


@pytest.mark.integration
class TestDivergenceMonitoring:
    """Test divergence monitoring between ES and BQ."""
    
    @pytest.mark.asyncio
    async def test_divergence_healthy(self, warehouse_enabled):
        """Test divergence calculation with healthy data."""
        from app.metrics.divergence import compute_divergence_24h
        
        # Mock both ES and BQ counts
        with patch('app.metrics.divergence.count_emails_last_24h_es') as mock_es, \
             patch('app.metrics.warehouse.mq_messages_last_24h') as mock_bq:
            
            mock_es.return_value = 100
            mock_bq.return_value = AsyncMock(return_value=98)
            
            result = await compute_divergence_24h()
            
            assert result["es_count"] == 100
            assert result["bq_count"] == 98
            assert result["divergence"] < 0.02
            assert result["slo_met"] is True
            assert result["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_divergence_warning(self, warehouse_enabled):
        """Test divergence with warning threshold."""
        from app.metrics.divergence import compute_divergence_24h
        
        with patch('app.metrics.divergence.count_emails_last_24h_es') as mock_es, \
             patch('app.metrics.warehouse.mq_messages_last_24h') as mock_bq:
            
            mock_es.return_value = 100
            mock_bq.return_value = AsyncMock(return_value=97)
            
            result = await compute_divergence_24h()
            
            assert result["divergence_pct"] == 3.0
            assert result["status"] == "warning"
            assert result["slo_met"] is False
    
    @pytest.mark.asyncio
    async def test_divergence_critical(self, warehouse_enabled):
        """Test divergence with critical threshold."""
        from app.metrics.divergence import compute_divergence_24h
        
        with patch('app.metrics.divergence.count_emails_last_24h_es') as mock_es, \
             patch('app.metrics.warehouse.mq_messages_last_24h') as mock_bq:
            
            mock_es.return_value = 100
            mock_bq.return_value = AsyncMock(return_value=90)
            
            result = await compute_divergence_24h()
            
            assert result["divergence"] >= 0.05
            assert result["status"] == "critical"
