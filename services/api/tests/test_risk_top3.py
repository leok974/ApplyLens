# services/api/tests/test_risk_top3.py
"""
Tests for Phase 4 AI Feature: Smart Risk Badge
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.security.analyzer import RiskAnalysis, RiskFlag

client = TestClient(app)


class TestRiskTop3Endpoint:
    """Test risk-top3 endpoint"""

    @patch("app.routers.security.ANALYZER")
    def test_risk_top3_returns_sorted_signals(self, mock_analyzer, mock_db_session):
        """Should return top 3 signals sorted by weight"""
        # Mock email
        mock_email = MagicMock()
        mock_email.id = "msg-123"
        mock_email.sender = "John Doe <john@example.com>"
        mock_email.subject = "Test email"
        mock_email.body_text = "Test body"
        mock_email.raw = {
            "payload": {
                "headers": [
                    {"name": "From", "value": "john@example.com"}
                ]
            }
        }
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_email
        
        # Mock risk analysis with 5 flags
        mock_analyzer.analyze.return_value = RiskAnalysis(
            risk_score=55,
            flags=[
                RiskFlag(signal="DMARC_FAIL", evidence="DMARC check failed", weight=25),
                RiskFlag(signal="NEW_DOMAIN", evidence="Domain registered recently", weight=10),
                RiskFlag(signal="SPF_FAIL", evidence="SPF check failed", weight=15),
                RiskFlag(signal="SUSPICIOUS_TLD", evidence=".xyz domain", weight=10),
                RiskFlag(signal="MALICIOUS_KEYWORD", evidence="urgent action", weight=10),
            ],
            quarantined=False
        )

        response = client.get("/api/security/risk-top3?message_id=msg-123")

        assert response.status_code == 200
        data = response.json()
        
        # Should return top 3
        assert "score" in data
        assert "signals" in data
        assert len(data["signals"]) == 3
        
        # Should be sorted by weight descending
        assert data["signals"][0]["id"] == "DMARC_FAIL"  # weight 25
        assert data["signals"][1]["id"] == "SPF_FAIL"    # weight 15
        assert data["signals"][2]["id"] in ["NEW_DOMAIN", "SUSPICIOUS_TLD", "MALICIOUS_KEYWORD"]  # weight 10
        
        # Should have human-readable labels
        assert data["signals"][0]["label"] == "DMARC Failed"
        assert "explain" in data["signals"][0]

    @patch("app.routers.security.ANALYZER")
    def test_risk_top3_handles_fewer_than_3_signals(self, mock_analyzer, mock_db_session):
        """Should handle cases with fewer than 3 signals"""
        mock_email = MagicMock()
        mock_email.id = "msg-456"
        mock_email.sender = "safe@trusted.com"
        mock_email.subject = "Safe email"
        mock_email.body_text = "Normal content"
        mock_email.raw = {"payload": {"headers": []}}
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_email
        
        # Only 1 signal
        mock_analyzer.analyze.return_value = RiskAnalysis(
            risk_score=10,
            flags=[
                RiskFlag(signal="NEW_DOMAIN", evidence="Domain is new", weight=10)
            ],
            quarantined=False
        )

        response = client.get("/api/security/risk-top3?message_id=msg-456")

        assert response.status_code == 200
        data = response.json()
        assert len(data["signals"]) == 1
        assert data["score"] == 10

    def test_risk_top3_message_not_found(self, mock_db_session):
        """Should return 404 for non-existent message"""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = client.get("/api/security/risk-top3?message_id=nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("app.routers.security.ANALYZER")
    def test_risk_top3_trusted_domain_signal(self, mock_analyzer, mock_db_session):
        """Should handle negative weight signals (trusted domain)"""
        mock_email = MagicMock()
        mock_email.id = "msg-789"
        mock_email.sender = "admin@google.com"
        mock_email.subject = "Trusted"
        mock_email.body_text = "Content"
        mock_email.raw = {"payload": {"headers": []}}
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_email
        
        mock_analyzer.analyze.return_value = RiskAnalysis(
            risk_score=0,
            flags=[
                RiskFlag(signal="TRUSTED_DOMAIN", evidence="google.com is trusted", weight=-15),
                RiskFlag(signal="NEW_DOMAIN", evidence="Domain check", weight=10),
            ],
            quarantined=False
        )

        response = client.get("/api/security/risk-top3?message_id=msg-789")

        assert response.status_code == 200
        data = response.json()
        assert len(data["signals"]) == 2
        
        # Should sort by absolute weight
        # TRUSTED_DOMAIN has |weight|=15, NEW_DOMAIN has |weight|=10
        assert data["signals"][0]["id"] == "TRUSTED_DOMAIN"


@pytest.fixture
def mock_db_session(monkeypatch):
    """Mock database session"""
    from unittest.mock import MagicMock
    from app.routers.security import get_db
    
    mock_session = MagicMock()
    
    def mock_get_db():
        yield mock_session
    
    # Note: This fixture should be combined with dependency override
    # in actual FastAPI testing
    return mock_session
