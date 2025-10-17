"""
Invariant & Gate Watcher - Phase 5.4 PR1+PR2

Watches evaluation results, metrics, and gates continuously.
Raises incidents when breaches occur, with deduplication.
Auto-creates issues in external trackers (GitHub/GitLab/Jira).

Background worker runs every N minutes, checks:
- Invariant failures from Phase 5 evals
- Budget overruns from Phase 5 budgets
- Planner canary regressions from Phase 5.1
- Gate violations (latency/quality/cost)
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from app.db import SessionLocal
from app.models_incident import Incident
from app.eval.models import EvalResult, InvariantResult
from app.models_runtime import RuntimeSettings

logger = logging.getLogger(__name__)

# Import adapters (optional - graceful degradation if not configured)
try:
    from app.intervene.adapters.base import IssueAdapterFactory
    from app.intervene.templates import render_incident_issue
    ADAPTERS_AVAILABLE = True
except ImportError:
    logger.warning("Issue adapters not available - incidents will be created without external issues")
    ADAPTERS_AVAILABLE = False


class InvariantWatcher:
    """
    Watches evaluation results and raises incidents on failures.
    
    Features:
    - Deduplication: Only create new incident if none open for same key
    - Rate limiting: Max N incidents per key per time window
    - Severity mapping: invariant priority → incident severity
    """
    
    def __init__(self, db: Session):
        self.db = db
        
    def check_invariants(self, lookback_minutes: int = 60) -> List[Incident]:
        """
        Check for invariant failures in recent eval results.
        
        Args:
            lookback_minutes: How far back to look for results
            
        Returns:
            List of newly created incidents
        """
        since = datetime.utcnow() - timedelta(minutes=lookback_minutes)
        
        # Query recent eval results with invariant failures
        results = (
            self.db.query(EvalResult)
            .filter(
                EvalResult.created_at >= since,
                EvalResult.invariant_results.isnot(None)
            )
            .order_by(desc(EvalResult.created_at))
            .all()
        )
        
        incidents = []
        for result in results:
            if not result.invariant_results:
                continue
                
            for inv_result in result.invariant_results:
                # Skip passed invariants
                if inv_result.get("passed", True):
                    continue
                    
                inv_id = inv_result.get("invariant_id")
                if not inv_id:
                    continue
                
                # Check if incident already open
                key = f"INV_{inv_id}"
                if self._has_open_incident("invariant", key):
                    continue
                
                # Check rate limit
                if self._is_rate_limited("invariant", key, hours=1):
                    logger.info(f"Rate limited incident for {key}")
                    continue
                
                # Create incident
                incident = self._create_invariant_incident(result, inv_result)
                incidents.append(incident)
                logger.info(f"Created incident {incident.id} for {key}")
        
        return incidents
    
    def check_budgets(self) -> List[Incident]:
        """
        Check for budget overruns.
        
        Returns:
            List of newly created incidents
        """
        # Query budget status from runtime settings
        budget_settings = (
            self.db.query(RuntimeSettings)
            .filter(RuntimeSettings.key.like("budget.%"))
            .all()
        )
        
        incidents = []
        for setting in budget_settings:
            value = setting.value
            if not isinstance(value, dict):
                continue
            
            # Check if over budget
            spent = value.get("spent", 0)
            limit = value.get("limit", float("inf"))
            
            if spent <= limit:
                continue
            
            # Extract agent/service from key
            key = setting.key  # e.g., budget.planner.daily
            
            # Check if incident already open
            if self._has_open_incident("budget", key):
                continue
            
            # Check rate limit
            if self._is_rate_limited("budget", key, hours=4):
                continue
            
            # Create incident
            incident = self._create_budget_incident(key, value)
            incidents.append(incident)
            logger.info(f"Created budget incident {incident.id} for {key}")
        
        return incidents
    
    def check_planner_regressions(self) -> List[Incident]:
        """
        Check for planner canary regressions.
        
        Returns:
            List of newly created incidents
        """
        # Query planner canary status
        canary_settings = (
            self.db.query(RuntimeSettings)
            .filter(RuntimeSettings.key.like("planner_canary.%.status"))
            .all()
        )
        
        incidents = []
        for setting in canary_settings:
            value = setting.value
            if not isinstance(value, dict):
                continue
            
            status = value.get("status")
            if status != "regressed":
                continue
            
            # Extract version from key
            # e.g., planner_canary.v2_insights_focus.status → v2_insights_focus
            parts = setting.key.split(".")
            if len(parts) < 2:
                continue
            version = parts[1]
            key = f"planner:{version}"
            
            # Check if incident already open
            if self._has_open_incident("planner", key):
                continue
            
            # Check rate limit
            if self._is_rate_limited("planner", key, hours=2):
                continue
            
            # Create incident
            incident = self._create_planner_incident(version, value)
            incidents.append(incident)
            logger.info(f"Created planner incident {incident.id} for {key}")
        
        return incidents
    
    def _has_open_incident(self, kind: str, key: str) -> bool:
        """Check if an open incident exists for this kind/key."""
        count = (
            self.db.query(Incident)
            .filter(
                Incident.kind == kind,
                Incident.key == key,
                Incident.status.in_(["open", "acknowledged", "mitigated"])
            )
            .count()
        )
        return count > 0
    
    def _is_rate_limited(self, kind: str, key: str, hours: int = 1) -> bool:
        """Check if we've created too many incidents recently."""
        since = datetime.utcnow() - timedelta(hours=hours)
        count = (
            self.db.query(Incident)
            .filter(
                Incident.kind == kind,
                Incident.key == key,
                Incident.created_at >= since
            )
            .count()
        )
        # Allow max 3 incidents per time window
        return count >= 3
    
    def _create_external_issue(self, incident: Incident) -> Optional[str]:
        """
        Create external issue (GitHub/GitLab/Jira) for incident.
        
        Returns:
            Issue URL if successful, None otherwise
        """
        if not ADAPTERS_AVAILABLE:
            return None
        
        try:
            # Get adapter config from runtime settings
            config_key = "interventions.issue_provider"
            provider_setting = (
                self.db.query(RuntimeSettings)
                .filter(RuntimeSettings.key == config_key)
                .first()
            )
            
            if not provider_setting:
                logger.debug("No issue provider configured")
                return None
            
            provider = provider_setting.value.get("provider")
            config = provider_setting.value.get("config", {})
            
            if not provider or not config:
                return None
            
            # Create adapter
            adapter = IssueAdapterFactory.create(provider, config)
            
            # Render template
            title, body = render_incident_issue(incident)
            
            # Create issue request
            from app.intervene.adapters.base import IssueCreateRequest
            request = IssueCreateRequest(
                title=title,
                body=body,
                labels=[incident.severity, incident.kind],
                priority=incident.severity,
            )
            
            # Create issue
            response = adapter.create_issue(request)
            
            if response.success:
                logger.info(f"Created external issue for incident {incident.id}: {response.issue_url}")
                return response.issue_url
            else:
                logger.error(f"Failed to create external issue: {response.error}")
                return None
                
        except Exception as e:
            logger.exception(f"Error creating external issue: {e}")
            return None
    
    def _create_invariant_incident(
        self,
        eval_result: EvalResult,
        inv_result: Dict[str, Any]
    ) -> Incident:
        """Create incident for invariant failure."""
        inv_id = inv_result.get("invariant_id", "UNKNOWN")
        inv_name = inv_result.get("name", inv_id)
        
        # Map priority to severity
        priority = inv_result.get("priority", "medium")
        severity_map = {
            "critical": "sev1",
            "high": "sev2",
            "medium": "sev3",
            "low": "sev4",
        }
        severity = severity_map.get(priority, "sev3")
        
        incident = Incident(
            kind="invariant",
            key=f"INV_{inv_id}",
            severity=severity,
            status="open",
            summary=f"Invariant failed: {inv_name}",
            details={
                "invariant_id": inv_id,
                "invariant_name": inv_name,
                "eval_result_id": eval_result.id,
                "agent": eval_result.agent,
                "task_id": eval_result.task_id,
                "failure_message": inv_result.get("message", ""),
                "evidence": inv_result.get("evidence", {}),
                "timestamp": eval_result.created_at.isoformat(),
            },
            playbooks=["rerun_eval", "check_agent_config"],
        )
        
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)
        
        # Create external issue
        issue_url = self._create_external_issue(incident)
        if issue_url:
            incident.issue_url = issue_url
            self.db.commit()
        
        return incident
    
    def _create_budget_incident(
        self,
        key: str,
        budget_data: Dict[str, Any]
    ) -> Incident:
        """Create incident for budget overrun."""
        spent = budget_data.get("spent", 0)
        limit = budget_data.get("limit", 0)
        overage = spent - limit
        
        # Budget overruns are sev2 (urgent but not critical)
        incident = Incident(
            kind="budget",
            key=key,
            severity="sev2",
            status="open",
            summary=f"Budget exceeded: {key}",
            details={
                "budget_key": key,
                "spent": spent,
                "limit": limit,
                "overage": overage,
                "overage_pct": (overage / limit * 100) if limit > 0 else 0,
            },
            playbooks=["reduce_traffic", "increase_budget", "pause_agent"],
        )
        
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)
        
        # Create external issue
        issue_url = self._create_external_issue(incident)
        if issue_url:
            incident.issue_url = issue_url
            self.db.commit()
        
        return incident
    
    def _create_planner_incident(
        self,
        version: str,
        canary_data: Dict[str, Any]
    ) -> Incident:
        """Create incident for planner regression."""
        metrics = canary_data.get("metrics", {})
        
        # Regressions are sev2 (need rollback)
        incident = Incident(
            kind="planner",
            key=f"planner:{version}",
            severity="sev2",
            status="open",
            summary=f"Planner canary regressed: {version}",
            details={
                "version": version,
                "metrics": metrics,
                "rollback_available": True,
            },
            playbooks=["rollback_planner", "analyze_regression"],
        )
        
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)
        
        # Create external issue
        issue_url = self._create_external_issue(incident)
        if issue_url:
            incident.issue_url = issue_url
            self.db.commit()
        
        return incident


def run_watcher_cycle():
    """
    Run one cycle of the watcher (called by scheduler).
    
    Checks invariants, budgets, and planner status.
    Creates incidents as needed.
    """
    logger.info("Starting watcher cycle")
    
    db = SessionLocal()
    try:
        watcher = InvariantWatcher(db)
        
        # Check all sources
        inv_incidents = watcher.check_invariants(lookback_minutes=60)
        budget_incidents = watcher.check_budgets()
        planner_incidents = watcher.check_planner_regressions()
        
        total = len(inv_incidents) + len(budget_incidents) + len(planner_incidents)
        logger.info(
            f"Watcher cycle complete: {total} incidents created "
            f"(invariants={len(inv_incidents)}, budgets={len(budget_incidents)}, "
            f"planner={len(planner_incidents)})"
        )
        
    except Exception as e:
        logger.error(f"Watcher cycle failed: {e}", exc_info=True)
    finally:
        db.close()
