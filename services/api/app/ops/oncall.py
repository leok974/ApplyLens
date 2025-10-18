"""
On-call rotation management and incident coordination.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field


class OnCallShift(str, Enum):
    """On-call shift types."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    MANAGER = "manager"


class IncidentSeverity(str, Enum):
    """Incident severity levels."""
    SEV1 = "sev1"  # Critical - complete outage
    SEV2 = "sev2"  # Major - significant degradation
    SEV3 = "sev3"  # Minor - limited impact
    SEV4 = "sev4"  # Low - minimal impact


class IncidentStatus(str, Enum):
    """Incident lifecycle status."""
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class OnCallSchedule(BaseModel):
    """On-call schedule entry."""
    user_email: str
    shift_type: OnCallShift
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"
    
    def is_active(self, at_time: Optional[datetime] = None) -> bool:
        """Check if schedule is currently active."""
        check_time = at_time or datetime.utcnow()
        return self.start_time <= check_time <= self.end_time


class Incident(BaseModel):
    """Incident record."""
    incident_id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.INVESTIGATING
    
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    commander: Optional[str] = None  # Incident commander email
    responders: List[str] = Field(default_factory=list)
    
    affected_agents: List[str] = Field(default_factory=list)
    related_alerts: List[str] = Field(default_factory=list)
    
    slack_channel: Optional[str] = None
    pagerduty_incident_id: Optional[str] = None
    
    timeline: List[Dict] = Field(default_factory=list)
    postmortem_url: Optional[str] = None
    
    @property
    def mttr_minutes(self) -> Optional[float]:
        """Mean time to resolution in minutes."""
        if not self.resolved_at:
            return None
        
        delta = self.resolved_at - self.triggered_at
        return delta.total_seconds() / 60
    
    @property
    def is_active(self) -> bool:
        """Check if incident is still active."""
        return self.status != IncidentStatus.RESOLVED
    
    def add_timeline_event(self, event_type: str, description: str, user: Optional[str] = None):
        """Add an event to the incident timeline."""
        self.timeline.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "description": description,
            "user": user,
        })


class OnCallRotation(BaseModel):
    """On-call rotation configuration."""
    name: str
    rotation_length_days: int = 7
    team_members: List[str] = Field(default_factory=list)
    current_primary: Optional[str] = None
    current_secondary: Optional[str] = None
    rotation_start_date: datetime = Field(default_factory=datetime.utcnow)


class OnCallManager:
    """Manages on-call rotations and incident coordination."""
    
    def __init__(self):
        self.schedules: List[OnCallSchedule] = []
        self.rotations: Dict[str, OnCallRotation] = {}
        self.incidents: Dict[str, Incident] = {}
    
    def add_schedule(self, schedule: OnCallSchedule):
        """Add an on-call schedule entry."""
        self.schedules.append(schedule)
    
    def get_current_oncall(self, shift_type: OnCallShift = OnCallShift.PRIMARY) -> Optional[str]:
        """Get current on-call engineer for a shift type."""
        now = datetime.utcnow()
        
        for schedule in self.schedules:
            if schedule.shift_type == shift_type and schedule.is_active(now):
                return schedule.user_email
        
        return None
    
    def create_incident(
        self,
        title: str,
        description: str,
        severity: IncidentSeverity,
        affected_agents: Optional[List[str]] = None,
        related_alerts: Optional[List[str]] = None,
    ) -> Incident:
        """
        Create a new incident and page on-call engineer.
        
        For SEV1/SEV2, page primary on-call.
        For SEV3/SEV4, create incident without immediate page.
        """
        import uuid
        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        
        incident = Incident(
            incident_id=incident_id,
            title=title,
            description=description,
            severity=severity,
            affected_agents=affected_agents or [],
            related_alerts=related_alerts or [],
        )
        
        # Assign commander (primary on-call for SEV1/SEV2)
        if severity in (IncidentSeverity.SEV1, IncidentSeverity.SEV2):
            primary = self.get_current_oncall(OnCallShift.PRIMARY)
            if primary:
                incident.commander = primary
                incident.responders.append(primary)
        
        incident.add_timeline_event(
            event_type="created",
            description=f"Incident created with severity {severity.value}",
        )
        
        self.incidents[incident_id] = incident
        
        # Page on-call for critical incidents
        if severity == IncidentSeverity.SEV1:
            self._page_oncall(incident)
        
        return incident
    
    def acknowledge_incident(self, incident_id: str, user: str) -> bool:
        """Acknowledge an incident."""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.acknowledged_at = datetime.utcnow()
        
        if not incident.commander:
            incident.commander = user
        
        if user not in incident.responders:
            incident.responders.append(user)
        
        incident.add_timeline_event(
            event_type="acknowledged",
            description=f"Incident acknowledged by {user}",
            user=user,
        )
        
        return True
    
    def update_incident_status(
        self,
        incident_id: str,
        status: IncidentStatus,
        user: str,
        notes: Optional[str] = None,
    ) -> bool:
        """Update incident status."""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        old_status = incident.status
        incident.status = status
        
        if status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.utcnow()
        
        description = f"Status changed from {old_status.value} to {status.value}"
        if notes:
            description += f": {notes}"
        
        incident.add_timeline_event(
            event_type="status_change",
            description=description,
            user=user,
        )
        
        return True
    
    def resolve_incident(self, incident_id: str, user: str, resolution: str) -> bool:
        """Resolve an incident."""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.utcnow()
        
        incident.add_timeline_event(
            event_type="resolved",
            description=f"Incident resolved: {resolution}",
            user=user,
        )
        
        return True
    
    def get_active_incidents(self, severity: Optional[IncidentSeverity] = None) -> List[Incident]:
        """Get all active incidents, optionally filtered by severity."""
        active = [
            incident for incident in self.incidents.values()
            if incident.is_active
        ]
        
        if severity:
            active = [inc for inc in active if inc.severity == severity]
        
        return sorted(active, key=lambda x: x.triggered_at, reverse=True)
    
    def get_incident_metrics(self, days: int = 7) -> Dict:
        """
        Get incident metrics for the past N days.
        
        Returns:
            - total_incidents: Total count
            - by_severity: Count per severity level
            - mttr_minutes: Mean time to resolution
            - active_count: Current active incidents
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        recent = [
            inc for inc in self.incidents.values()
            if inc.triggered_at >= cutoff
        ]
        
        by_severity = {
            IncidentSeverity.SEV1: 0,
            IncidentSeverity.SEV2: 0,
            IncidentSeverity.SEV3: 0,
            IncidentSeverity.SEV4: 0,
        }
        
        resolution_times = []
        
        for incident in recent:
            by_severity[incident.severity] += 1
            
            if incident.mttr_minutes:
                resolution_times.append(incident.mttr_minutes)
        
        avg_mttr = None
        if resolution_times:
            avg_mttr = sum(resolution_times) / len(resolution_times)
        
        active_count = len(self.get_active_incidents())
        
        return {
            "total_incidents": len(recent),
            "by_severity": {k.value: v for k, v in by_severity.items()},
            "mttr_minutes": avg_mttr,
            "active_count": active_count,
            "period_days": days,
        }
    
    def _page_oncall(self, incident: Incident):
        """
        Page on-call engineer for critical incident.
        
        In production, this would:
        - Send PagerDuty alert
        - Create Slack incident channel
        - Send SMS to primary on-call
        """
        # Placeholder for integration
        pass
    
    def generate_weekly_report(self) -> str:
        """
        Generate weekly on-call report.
        
        Includes:
        - Incident summary
        - Response times
        - Top affected agents
        - Recommendations
        """
        metrics = self.get_incident_metrics(days=7)
        
        report = f"""# Weekly On-Call Report
        
**Period:** Last 7 days
**Generated:** {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}

## Incident Summary

- **Total Incidents:** {metrics['total_incidents']}
- **Active Incidents:** {metrics['active_count']}
- **Mean Time to Resolution:** {metrics['mttr_minutes']:.1f} minutes
        
### By Severity

- **SEV1 (Critical):** {metrics['by_severity']['sev1']}
- **SEV2 (Major):** {metrics['by_severity']['sev2']}
- **SEV3 (Minor):** {metrics['by_severity']['sev3']}
- **SEV4 (Low):** {metrics['by_severity']['sev4']}

## Recent Incidents

"""
        
        recent = self.get_active_incidents()[:5]
        
        for incident in recent:
            report += f"""
### {incident.incident_id}: {incident.title}

- **Severity:** {incident.severity.value}
- **Status:** {incident.status.value}
- **Triggered:** {incident.triggered_at.strftime("%Y-%m-%d %H:%M")}
- **Commander:** {incident.commander or 'Unassigned'}
"""
            
            if incident.mttr_minutes:
                report += f"- **MTTR:** {incident.mttr_minutes:.1f} minutes\n"
        
        report += "\n## Recommendations\n\n"
        
        if metrics['by_severity']['sev1'] > 0:
            report += "- Review SEV1 incidents for systemic issues\n"
        
        if metrics['mttr_minutes'] and metrics['mttr_minutes'] > 30:
            report += "- MTTR above 30 minutes - review response procedures\n"
        
        if metrics['active_count'] > 3:
            report += "- High number of active incidents - consider additional resources\n"
        
        return report


# Global instance
_oncall_manager = None


def get_oncall_manager() -> OnCallManager:
    """Get global on-call manager instance."""
    global _oncall_manager
    if _oncall_manager is None:
        _oncall_manager = OnCallManager()
    return _oncall_manager
