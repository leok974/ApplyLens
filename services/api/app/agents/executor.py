"""Agent executor - runs plans and tracks execution."""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict


class Executor:
    """Executes agent plans and tracks run state.
    
    Manages execution lifecycle:
    - Creates run records with unique IDs
    - Tracks status (running -> succeeded/failed)
    - Captures logs and artifacts
    - Stores results in the run store
    """
    
    def __init__(self, run_store: Dict[str, dict]):
        """Initialize executor with a run store.
        
        Args:
            run_store: Dictionary to store run records by run_id
        """
        self.run_store = run_store
    
    def execute(
        self, 
        plan: Dict[str, Any], 
        handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a plan using the provided handler.
        
        Args:
            plan: Execution plan from planner
            handler: Callable that executes the plan
            
        Returns:
            Run record with status, logs, and artifacts
        """
        run_id = str(uuid.uuid4())
        run = {
            "run_id": run_id,
            "status": "running",
            "started_at": datetime.utcnow(),
            "logs": [f"start agent={plan['agent']} objective={plan['objective']}"],
            "finished_at": None,
            "artifacts": {},
        }
        self.run_store[run_id] = run
        
        try:
            result = handler(plan)
            run.update({
                "status": "succeeded",
                "finished_at": datetime.utcnow(),
                "artifacts": result or {},
            })
        except Exception as e:
            run.update({
                "status": "failed",
                "finished_at": datetime.utcnow(),
                "logs": run["logs"] + [f"error: {e!r}"],
            })
        
        return run
