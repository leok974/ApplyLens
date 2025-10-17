"""Agent executor - runs plans and tracks execution."""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict

from .audit import AgentAuditor
from ..observability import record_agent_run


class Executor:
    """Executes agent plans and tracks run state.
    
    Manages execution lifecycle:
    - Creates run records with unique IDs
    - Tracks status (running -> succeeded/failed)
    - Captures logs and artifacts
    - Stores results in the run store
    - Logs to audit trail if enabled
    """
    
    def __init__(self, run_store: Dict[str, dict], auditor: AgentAuditor | None = None):
        """Initialize executor with a run store.
        
        Args:
            run_store: Dictionary to store run records by run_id
            auditor: Optional auditor for database logging
        """
        self.run_store = run_store
        self.auditor = auditor
    
    def execute(
        self, 
        plan: Dict[str, Any], 
        handler: Callable[[Dict[str, Any]], Dict[str, Any]],
        user_email: str | None = None
    ) -> Dict[str, Any]:
        """Execute a plan using the provided handler.
        
        Args:
            plan: Execution plan from planner
            handler: Callable that executes the plan
            user_email: Optional user email for audit logging
            
        Returns:
            Run record with status, logs, and artifacts
        """
        run_id = str(uuid.uuid4())
        t0 = time.perf_counter()
        
        run = {
            "run_id": run_id,
            "status": "running",
            "started_at": datetime.utcnow(),
            "logs": [f"start agent={plan['agent']} objective={plan['objective']}"],
            "finished_at": None,
            "artifacts": {},
        }
        self.run_store[run_id] = run
        
        # Log start to audit trail
        if self.auditor:
            self.auditor.log_start(
                run_id=run_id,
                agent=plan["agent"],
                objective=plan["objective"],
                plan=plan,
                user_email=user_email
            )
        
        try:
            result = handler(plan)
            duration_ms = (time.perf_counter() - t0) * 1000
            
            run.update({
                "status": "succeeded",
                "finished_at": datetime.utcnow(),
                "artifacts": result or {},
            })
            
            # Log success to audit trail
            if self.auditor:
                self.auditor.log_finish(
                    run_id=run_id,
                    status="succeeded",
                    artifacts=result or {},
                    duration_ms=duration_ms
                )
            
            # Record metrics
            record_agent_run(
                agent=plan["agent"],
                status="succeeded",
                duration_ms=duration_ms
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000
            error_msg = f"{type(e).__name__}: {e}"
            
            run.update({
                "status": "failed",
                "finished_at": datetime.utcnow(),
                "logs": run["logs"] + [f"error: {e!r}"],
            })
            
            # Log failure to audit trail
            if self.auditor:
                self.auditor.log_finish(
                    run_id=run_id,
                    status="failed",
                    error=error_msg,
                    duration_ms=duration_ms
                )
            
            # Record metrics
            record_agent_run(
                agent=plan["agent"],
                status="failed",
                duration_ms=duration_ms
            )
        
        return run
