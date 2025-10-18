"""
Tests for on-call rotation and incident management.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.ops.oncall import (
    OnCallSchedule,
    OnCallShift,
    Incident,
    IncidentSeverity,
    IncidentStatus,
    OnCallRotation,
    OnCallManager,
)
from app.ops.pagerduty import (
    PagerDutyClient,
    PagerDutyEvent,
    PagerDutyEventAction,
    PagerDutySeverity,
    PagerDutyIntegration,
)
from app.ops.slack import (
    SlackClient,
    SlackIncidentChannel,
)


class TestOnCallSchedule:
    """Test on-call schedule."""
    
    def test_schedule_creation(self):
        """Test creating an on-call schedule."""
        now = datetime.utcnow()
        end = now + timedelta(days=7)
        
        schedule = OnCallSchedule(
            user_email="oncall@example.com",
            shift_type=OnCallShift.PRIMARY,
            start_time=now,
            end_time=end,
        )
        
        assert schedule.user_email == "oncall@example.com"
        assert schedule.shift_type == OnCallShift.PRIMARY
        assert schedule.is_active() is True
    
    def test_schedule_active_check(self):
        """Test checking if schedule is active."""
        now = datetime.utcnow()
        
        # Active schedule
        schedule = OnCallSchedule(
            user_email="oncall@example.com",
            shift_type=OnCallShift.PRIMARY,
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )
        assert schedule.is_active(now) is True
        
        # Past schedule
        past_schedule = OnCallSchedule(
            user_email="oncall@example.com",
            shift_type=OnCallShift.PRIMARY,
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=1),
        )
        assert past_schedule.is_active(now) is False


class TestIncident:
    """Test incident model."""
    
    def test_incident_creation(self):
        """Test creating an incident."""
        incident = Incident(
            incident_id="INC-12345678",
            title="API Outage",
            description="500 errors on /health endpoint",
            severity=IncidentSeverity.SEV1,
        )
        
        assert incident.incident_id == "INC-12345678"
        assert incident.severity == IncidentSeverity.SEV1
        assert incident.status == IncidentStatus.INVESTIGATING
        assert incident.is_active is True
    
    def test_mttr_calculation(self):
        """Test MTTR calculation."""
        now = datetime.utcnow()
        
        incident = Incident(
            incident_id="INC-12345678",
            title="Test Incident",
            description="Test",
            severity=IncidentSeverity.SEV2,
        )
        incident.triggered_at = now
        
        # No resolution yet
        assert incident.mttr_minutes is None
        
        # Resolve after 30 minutes
        incident.resolved_at = now + timedelta(minutes=30)
        assert incident.mttr_minutes == 30.0
    
    def test_timeline_events(self):
        """Test adding timeline events."""
        incident = Incident(
            incident_id="INC-12345678",
            title="Test Incident",
            description="Test",
            severity=IncidentSeverity.SEV3,
        )
        
        incident.add_timeline_event(
            event_type="investigation_update",
            description="Checked logs, found 500 errors",
            user="oncall@example.com",
        )
        
        assert len(incident.timeline) == 1
        assert incident.timeline[0]["event_type"] == "investigation_update"
        assert incident.timeline[0]["user"] == "oncall@example.com"


class TestOnCallManager:
    """Test on-call manager."""
    
    @pytest.fixture
    def manager(self):
        """Create on-call manager."""
        return OnCallManager()
    
    @pytest.fixture
    def active_schedule(self):
        """Create active on-call schedule."""
        now = datetime.utcnow()
        return OnCallSchedule(
            user_email="primary@example.com",
            shift_type=OnCallShift.PRIMARY,
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=23),
        )
    
    def test_add_schedule(self, manager, active_schedule):
        """Test adding a schedule."""
        manager.add_schedule(active_schedule)
        
        assert len(manager.schedules) == 1
        assert manager.schedules[0].user_email == "primary@example.com"
    
    def test_get_current_oncall(self, manager, active_schedule):
        """Test getting current on-call engineer."""
        manager.add_schedule(active_schedule)
        
        oncall = manager.get_current_oncall(OnCallShift.PRIMARY)
        assert oncall == "primary@example.com"
        
        # No secondary on-call
        secondary = manager.get_current_oncall(OnCallShift.SECONDARY)
        assert secondary is None
    
    def test_create_incident_sev1(self, manager, active_schedule):
        """Test creating a SEV1 incident."""
        manager.add_schedule(active_schedule)
        
        incident = manager.create_incident(
            title="API Complete Outage",
            description="All endpoints returning 503",
            severity=IncidentSeverity.SEV1,
            affected_agents=["inbox.triage", "knowledge.search"],
        )
        
        assert incident.severity == IncidentSeverity.SEV1
        assert incident.commander == "primary@example.com"
        assert "primary@example.com" in incident.responders
        assert len(incident.timeline) == 1
    
    def test_create_incident_sev3(self, manager):
        """Test creating a SEV3 incident (no immediate page)."""
        incident = manager.create_incident(
            title="Minor UI Issue",
            description="Button misaligned",
            severity=IncidentSeverity.SEV3,
        )
        
        assert incident.severity == IncidentSeverity.SEV3
        assert incident.commander is None  # Not assigned for SEV3
    
    def test_acknowledge_incident(self, manager):
        """Test acknowledging an incident."""
        incident = manager.create_incident(
            title="Test Incident",
            description="Test",
            severity=IncidentSeverity.SEV2,
        )
        
        success = manager.acknowledge_incident(incident.incident_id, "oncall@example.com")
        
        assert success is True
        assert incident.acknowledged_at is not None
        assert incident.commander == "oncall@example.com"
        assert len(incident.timeline) == 2  # Created + acknowledged
    
    def test_update_incident_status(self, manager):
        """Test updating incident status."""
        incident = manager.create_incident(
            title="Test Incident",
            description="Test",
            severity=IncidentSeverity.SEV2,
        )
        
        success = manager.update_incident_status(
            incident.incident_id,
            IncidentStatus.IDENTIFIED,
            "oncall@example.com",
            notes="Root cause identified",
        )
        
        assert success is True
        assert incident.status == IncidentStatus.IDENTIFIED
        assert len(incident.timeline) == 2
    
    def test_resolve_incident(self, manager):
        """Test resolving an incident."""
        incident = manager.create_incident(
            title="Test Incident",
            description="Test",
            severity=IncidentSeverity.SEV2,
        )
        
        success = manager.resolve_incident(
            incident.incident_id,
            "oncall@example.com",
            "Fixed by restarting service",
        )
        
        assert success is True
        assert incident.status == IncidentStatus.RESOLVED
        assert incident.resolved_at is not None
        assert incident.is_active is False
    
    def test_get_active_incidents(self, manager):
        """Test getting active incidents."""
        # Create multiple incidents
        manager.create_incident("Incident 1", "Test", IncidentSeverity.SEV1)
        manager.create_incident("Incident 2", "Test", IncidentSeverity.SEV2)
        inc3 = manager.create_incident("Incident 3", "Test", IncidentSeverity.SEV3)
        
        # Resolve one
        manager.resolve_incident(inc3.incident_id, "oncall@example.com", "Fixed")
        
        active = manager.get_active_incidents()
        assert len(active) == 2
        
        # Filter by severity
        sev1 = manager.get_active_incidents(severity=IncidentSeverity.SEV1)
        assert len(sev1) == 1
    
    def test_get_incident_metrics(self, manager):
        """Test getting incident metrics."""
        # Create incidents
        inc1 = manager.create_incident("Inc 1", "Test", IncidentSeverity.SEV1)
        inc2 = manager.create_incident("Inc 2", "Test", IncidentSeverity.SEV2)
        inc3 = manager.create_incident("Inc 3", "Test", IncidentSeverity.SEV1)
        
        # Resolve some
        manager.resolve_incident(inc1.incident_id, "oncall@example.com", "Fixed")
        manager.resolve_incident(inc2.incident_id, "oncall@example.com", "Fixed")
        
        metrics = manager.get_incident_metrics(days=7)
        
        assert metrics["total_incidents"] == 3
        assert metrics["by_severity"]["sev1"] == 2
        assert metrics["by_severity"]["sev2"] == 1
        assert metrics["active_count"] == 1
        assert metrics["mttr_minutes"] is not None
    
    def test_generate_weekly_report(self, manager):
        """Test generating weekly report."""
        # Create some incidents
        manager.create_incident("Incident 1", "Test", IncidentSeverity.SEV1)
        manager.create_incident("Incident 2", "Test", IncidentSeverity.SEV2)
        
        report = manager.generate_weekly_report()
        
        assert "Weekly On-Call Report" in report
        assert "Total Incidents" in report
        assert "SEV1" in report
        assert "Recommendations" in report


class TestPagerDutyClient:
    """Test PagerDuty client."""
    
    def test_event_creation(self):
        """Test creating a PagerDuty event."""
        event = PagerDutyEvent.create_trigger(
            routing_key="test-key",
            summary="Test Alert",
            source="applylens-test",
            severity=PagerDutySeverity.CRITICAL,
            dedup_key="test-123",
            custom_details={"agent": "test.agent"},
        )
        
        assert event.event_action == PagerDutyEventAction.TRIGGER
        assert event.dedup_key == "test-123"
        assert event.payload["summary"] == "Test Alert"
        assert event.payload["severity"] == "critical"
    
    @pytest.mark.asyncio
    async def test_send_event_mock(self):
        """Test sending event (mocked)."""
        client = PagerDutyClient(routing_key="test-key")
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"status": "success", "dedup_key": "test-123"}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response
            
            event = PagerDutyEvent.create_trigger(
                routing_key="test-key",
                summary="Test",
                source="test",
                severity=PagerDutySeverity.CRITICAL,
                dedup_key="test-123",
            )
            
            result = await client.send_event(event)
            
            assert result["status"] == "success"
            assert result["dedup_key"] == "test-123"


class TestPagerDutyIntegration:
    """Test PagerDuty integration."""
    
    @pytest.mark.asyncio
    async def test_alert_slo_violation(self):
        """Test alerting on SLO violation."""
        integration = PagerDutyIntegration(routing_key="test-key")
        
        with patch.object(integration.client, "trigger_incident", new_callable=AsyncMock) as mock_trigger:
            mock_trigger.return_value = "test-dedup-key"
            
            dedup_key = await integration.alert_slo_violation(
                agent_name="inbox.triage",
                metric="latency_p95",
                severity="CRITICAL",
                threshold=1500,
                actual=2500,
                incident_id="INC-12345678",
            )
            
            assert dedup_key == "test-dedup-key"
            mock_trigger.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_alert_incident(self):
        """Test creating PagerDuty incident."""
        integration = PagerDutyIntegration(routing_key="test-key")
        
        with patch.object(integration.client, "trigger_incident", new_callable=AsyncMock) as mock_trigger:
            mock_trigger.return_value = "test-dedup-key"
            
            dedup_key = await integration.alert_incident(
                incident_id="INC-12345678",
                title="API Outage",
                description="Complete service outage",
                severity="sev1",
                affected_agents=["inbox.triage"],
            )
            
            assert dedup_key == "test-dedup-key"
            mock_trigger.assert_called_once()


class TestSlackClient:
    """Test Slack client."""
    
    @pytest.mark.asyncio
    async def test_post_message(self):
        """Test posting a Slack message."""
        client = SlackClient(bot_token="xoxb-test-token")
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True, "ts": "1234567890.123456"}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response
            
            result = await client.post_message(
                channel="#test",
                text="Test message",
            )
            
            assert result["ok"] is True
            assert "ts" in result


class TestSlackIncidentChannel:
    """Test Slack incident channel management."""
    
    @pytest.mark.asyncio
    async def test_post_timeline_update(self):
        """Test posting timeline update."""
        mock_client = MagicMock()
        mock_client.post_message = AsyncMock(return_value={"ts": "1234567890.123456"})
        
        channel = SlackIncidentChannel(slack_client=mock_client)
        
        ts = await channel.post_timeline_update(
            channel_id="C12345",
            incident_id="INC-12345678",
            update="Investigating root cause",
            user="oncall@example.com",
        )
        
        assert ts == "1234567890.123456"
        mock_client.post_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_post_resolution(self):
        """Test posting incident resolution."""
        mock_client = MagicMock()
        mock_client.post_message = AsyncMock(return_value={"ts": "1234567890.123456"})
        
        channel = SlackIncidentChannel(slack_client=mock_client)
        
        ts = await channel.post_resolution(
            channel_id="C12345",
            incident_id="INC-12345678",
            resolution="Fixed by restarting service",
            mttr_minutes=15.5,
            user="oncall@example.com",
        )
        
        assert ts == "1234567890.123456"
        mock_client.post_message.assert_called_once()
