"""Agent audit logging module.

Handles persistence of agent execution records to database.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.orm import Session

from ..config import agent_settings
from ..db import get_db
from ..models import AgentAuditLog


class AgentAuditor:
    """Auditor for agent executions.
    
    Records agent runs to database for compliance, debugging, and analytics.
    Can be disabled via AGENT_AUDIT_ENABLED=false.
    """
    
    def __init__(self, db_session: Session | None = None):
        """Initialize auditor.
        
        Args:
            db_session: Optional database session (for testing)
        """
        self.db_session = db_session
        self._enabled = agent_settings.AGENT_AUDIT_ENABLED
    
    def _get_session(self) -> Session:
        """Get database session.
        
        Returns:
            SQLAlchemy session
        """
        if self.db_session:
            return self.db_session
        return next(get_db())
    
    def log_start(
        self,
        run_id: str,
        agent: str,
        objective: str,
        plan: Dict[str, Any],
        user_email: str | None = None
    ) -> None:
        """Log agent run start.
        
        Args:
            run_id: Unique run identifier
            agent: Agent name
            objective: Run objective
            plan: Execution plan
            user_email: User who triggered the run
        """
        if not self._enabled:
            return
        
        try:
            session = self._get_session()
            
            log = AgentAuditLog(
                run_id=run_id,
                agent=agent,
                objective=objective,
                status="running",
                started_at=datetime.now(timezone.utc),
                plan=plan,
                user_email=user_email,
                dry_run=plan.get("dry_run", True)
            )
            
            session.add(log)
            session.commit()
        except Exception as e:
            # Don't fail the agent run if audit logging fails
            print(f"Warning: Agent audit log failed to record start: {e}")
    
    def log_finish(
        self,
        run_id: str,
        status: str,
        artifacts: Dict[str, Any] | None = None,
        error: str | None = None,
        duration_ms: float | None = None
    ) -> None:
        """Log agent run completion.
        
        Args:
            run_id: Run identifier
            status: Final status (succeeded, failed, canceled)
            artifacts: Run artifacts
            error: Error message if failed
            duration_ms: Execution duration in milliseconds
        """
        if not self._enabled:
            return
        
        try:
            session = self._get_session()
            
            log = session.query(AgentAuditLog).filter_by(run_id=run_id).first()
            if not log:
                print(f"Warning: No audit log found for run_id={run_id}")
                return
            
            log.status = status
            log.finished_at = datetime.now(timezone.utc)
            log.duration_ms = duration_ms
            log.artifacts = artifacts or {}
            log.error = error
            
            session.commit()
        except Exception as e:
            print(f"Warning: Agent audit log failed to record finish: {e}")
    
    def get_run(self, run_id: str) -> AgentAuditLog | None:
        """Get audit log for a run.
        
        Args:
            run_id: Run identifier
            
        Returns:
            Audit log or None
        """
        if not self._enabled:
            return None
        
        try:
            session = self._get_session()
            return session.query(AgentAuditLog).filter_by(run_id=run_id).first()
        except Exception:
            return None
    
    def get_recent_runs(
        self,
        agent: str | None = None,
        limit: int = 100
    ) -> list[AgentAuditLog]:
        """Get recent agent runs.
        
        Args:
            agent: Filter by agent name (optional)
            limit: Maximum number of runs to return
            
        Returns:
            List of audit logs ordered by started_at DESC
        """
        if not self._enabled:
            return []
        
        try:
            session = self._get_session()
            query = session.query(AgentAuditLog)
            
            if agent:
                query = query.filter_by(agent=agent)
            
            return query.order_by(AgentAuditLog.started_at.desc()).limit(limit).all()
        except Exception:
            return []


# Global auditor instance (can be overridden for testing)
_auditor: AgentAuditor | None = None


def get_auditor() -> AgentAuditor:
    """Get global auditor instance.
    
    Returns:
        Agent auditor
    """
    global _auditor
    if _auditor is None:
        _auditor = AgentAuditor()
    return _auditor


def set_auditor(auditor: AgentAuditor) -> None:
    """Set global auditor instance (for testing).
    
    Args:
        auditor: Auditor instance
    """
    global _auditor
    _auditor = auditor
