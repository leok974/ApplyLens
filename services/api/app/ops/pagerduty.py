"""
PagerDuty integration for incident alerting and escalation.
"""

import os
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum
import httpx
from pydantic import BaseModel


class PagerDutyEventAction(str, Enum):
    """PagerDuty event actions."""
    TRIGGER = "trigger"
    ACKNOWLEDGE = "acknowledge"
    RESOLVE = "resolve"


class PagerDutySeverity(str, Enum):
    """PagerDuty severity levels."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class PagerDutyEvent(BaseModel):
    """PagerDuty Events API v2 event."""
    routing_key: str
    event_action: PagerDutyEventAction
    dedup_key: Optional[str] = None
    
    payload: Optional[Dict] = None
    
    @classmethod
    def create_trigger(
        cls,
        routing_key: str,
        summary: str,
        source: str,
        severity: PagerDutySeverity,
        dedup_key: str,
        custom_details: Optional[Dict] = None,
    ) -> "PagerDutyEvent":
        """Create a trigger event."""
        return cls(
            routing_key=routing_key,
            event_action=PagerDutyEventAction.TRIGGER,
            dedup_key=dedup_key,
            payload={
                "summary": summary,
                "source": source,
                "severity": severity.value,
                "timestamp": datetime.utcnow().isoformat(),
                "custom_details": custom_details or {},
            },
        )


class PagerDutyClient:
    """Client for PagerDuty Events API v2."""
    
    EVENTS_API_URL = "https://events.pagerduty.com/v2/enqueue"
    
    def __init__(self, routing_key: Optional[str] = None):
        """
        Initialize PagerDuty client.
        
        Args:
            routing_key: Integration key from PagerDuty service.
                         If not provided, reads from PAGERDUTY_ROUTING_KEY env var.
        """
        self.routing_key = routing_key or os.getenv("PAGERDUTY_ROUTING_KEY")
        
        if not self.routing_key:
            raise ValueError("PagerDuty routing key not provided")
    
    async def send_event(self, event: PagerDutyEvent) -> Dict:
        """
        Send an event to PagerDuty.
        
        Returns:
            Response from PagerDuty API with status and dedup_key.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.EVENTS_API_URL,
                json=event.dict(exclude_none=True),
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
    
    async def trigger_incident(
        self,
        summary: str,
        source: str,
        severity: PagerDutySeverity,
        dedup_key: str,
        custom_details: Optional[Dict] = None,
    ) -> str:
        """
        Trigger a new PagerDuty incident.
        
        Args:
            summary: Brief description of the incident
            source: Source of the alert (e.g., "applylens-api")
            severity: Severity level
            dedup_key: Unique key for deduplication
            custom_details: Additional context
        
        Returns:
            dedup_key for tracking the incident
        """
        event = PagerDutyEvent.create_trigger(
            routing_key=self.routing_key,
            summary=summary,
            source=source,
            severity=severity,
            dedup_key=dedup_key,
            custom_details=custom_details,
        )
        
        result = await self.send_event(event)
        return result.get("dedup_key", dedup_key)
    
    async def acknowledge_incident(self, dedup_key: str) -> Dict:
        """Acknowledge a PagerDuty incident."""
        event = PagerDutyEvent(
            routing_key=self.routing_key,
            event_action=PagerDutyEventAction.ACKNOWLEDGE,
            dedup_key=dedup_key,
        )
        
        return await self.send_event(event)
    
    async def resolve_incident(self, dedup_key: str) -> Dict:
        """Resolve a PagerDuty incident."""
        event = PagerDutyEvent(
            routing_key=self.routing_key,
            event_action=PagerDutyEventAction.RESOLVE,
            dedup_key=dedup_key,
        )
        
        return await self.send_event(event)


class PagerDutyIntegration:
    """
    High-level PagerDuty integration for ApplyLens.
    
    Manages incident creation, escalation, and lifecycle.
    """
    
    def __init__(self, routing_key: Optional[str] = None):
        self.client = PagerDutyClient(routing_key=routing_key)
    
    async def alert_slo_violation(
        self,
        agent_name: str,
        metric: str,
        severity: str,
        threshold: float,
        actual: float,
        incident_id: str,
    ) -> str:
        """
        Alert on-call about SLO violation.
        
        Args:
            agent_name: Name of the agent
            metric: Metric that violated SLO
            severity: Severity level (CRITICAL, WARNING, INFO)
            threshold: SLO threshold
            actual: Actual measured value
            incident_id: Internal incident ID
        
        Returns:
            PagerDuty dedup_key
        """
        # Map severity to PagerDuty
        pd_severity = {
            "CRITICAL": PagerDutySeverity.CRITICAL,
            "WARNING": PagerDutySeverity.WARNING,
            "INFO": PagerDutySeverity.INFO,
        }.get(severity, PagerDutySeverity.ERROR)
        
        summary = f"SLO Violation: {agent_name} - {metric}"
        
        custom_details = {
            "agent": agent_name,
            "metric": metric,
            "severity": severity,
            "threshold": threshold,
            "actual": actual,
            "incident_id": incident_id,
            "runbook_url": f"https://docs.applylens.io/runbooks/{agent_name}",
        }
        
        dedup_key = f"applylens-slo-{agent_name}-{metric}"
        
        return await self.client.trigger_incident(
            summary=summary,
            source="applylens-slo-monitor",
            severity=pd_severity,
            dedup_key=dedup_key,
            custom_details=custom_details,
        )
    
    async def alert_incident(
        self,
        incident_id: str,
        title: str,
        description: str,
        severity: str,
        affected_agents: List[str],
    ) -> str:
        """
        Create PagerDuty incident for system incident.
        
        Args:
            incident_id: Internal incident ID
            title: Incident title
            description: Detailed description
            severity: SEV1, SEV2, SEV3, SEV4
            affected_agents: List of affected agents
        
        Returns:
            PagerDuty dedup_key
        """
        # Map incident severity to PagerDuty
        pd_severity_map = {
            "sev1": PagerDutySeverity.CRITICAL,
            "sev2": PagerDutySeverity.ERROR,
            "sev3": PagerDutySeverity.WARNING,
            "sev4": PagerDutySeverity.INFO,
        }
        pd_severity = pd_severity_map.get(severity.lower(), PagerDutySeverity.ERROR)
        
        summary = f"{severity.upper()}: {title}"
        
        custom_details = {
            "incident_id": incident_id,
            "description": description,
            "severity": severity,
            "affected_agents": ", ".join(affected_agents),
            "incident_url": f"https://app.applylens.io/incidents/{incident_id}",
        }
        
        dedup_key = f"applylens-incident-{incident_id}"
        
        return await self.client.trigger_incident(
            summary=summary,
            source="applylens-incident-manager",
            severity=pd_severity,
            dedup_key=dedup_key,
            custom_details=custom_details,
        )
    
    async def acknowledge(self, incident_id: str) -> Dict:
        """Acknowledge incident in PagerDuty."""
        dedup_key = f"applylens-incident-{incident_id}"
        return await self.client.acknowledge_incident(dedup_key)
    
    async def resolve(self, incident_id: str) -> Dict:
        """Resolve incident in PagerDuty."""
        dedup_key = f"applylens-incident-{incident_id}"
        return await self.client.resolve_incident(dedup_key)


# Global instance
_pagerduty_integration = None


def get_pagerduty_integration() -> PagerDutyIntegration:
    """Get global PagerDuty integration instance."""
    global _pagerduty_integration
    if _pagerduty_integration is None:
        _pagerduty_integration = PagerDutyIntegration()
    return _pagerduty_integration
