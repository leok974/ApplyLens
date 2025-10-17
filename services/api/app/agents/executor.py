"""Agent executor - runs plans and tracks execution."""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from .audit import AgentAuditor
from ..events import AgentEvent, get_event_bus
from ..observability import record_agent_run
from ..policy import PolicyEngine, Budget
from ..policy.defaults import get_default_policies


class Executor:
    """Executes agent plans and tracks run state.
    
    Manages execution lifecycle:
    - Creates run records with unique IDs
    - Tracks status (running -> succeeded/failed)
    - Captures logs and artifacts
    - Stores results in the run store
    - Logs to audit trail if enabled
    - Emits events to event bus for real-time updates
    """
    
    def __init__(
        self, 
        run_store: Dict[str, dict], 
        auditor: AgentAuditor | None = None,
        event_bus_enabled: bool = True,
        policy_engine: Optional[PolicyEngine] = None
    ):
        """Initialize executor with a run store.
        
        Args:
            run_store: Dictionary to store run records by run_id
            auditor: Optional auditor for database logging
            event_bus_enabled: Whether to emit events to event bus (default: True)
            policy_engine: Optional policy engine for authorization (default: uses default policies)
        """
        self.run_store = run_store
        self.auditor = auditor
        self.event_bus_enabled = event_bus_enabled
        if event_bus_enabled:
            self.event_bus = get_event_bus()
        else:
            self.event_bus = None
        
        # Initialize policy engine with default policies if not provided
        if policy_engine is None:
            self.policy_engine = PolicyEngine(get_default_policies())
        else:
            self.policy_engine = policy_engine
    
    def execute(
        self, 
        plan: Dict[str, Any], 
        handler: Callable[[Dict[str, Any]], Dict[str, Any]],
        user_email: str | None = None,
        budget_ms: int | None = None,
        budget_ops: int | None = None,
        budget_cost_cents: int | None = None,
        allow_actions: bool = False
    ) -> Dict[str, Any]:
        """Execute a plan using the provided handler.
        
        Args:
            plan: Execution plan from planner
            handler: Callable that executes the plan
            user_email: Optional user email for audit logging
            budget_ms: Optional max execution time in milliseconds
            budget_ops: Optional max number of operations
            budget_cost_cents: Optional max cost in cents
            allow_actions: Whether to allow actions (requires dry_run=false)
            
        Returns:
            Run record with status, logs, and artifacts
        """
        run_id = str(uuid.uuid4())
        t0 = time.perf_counter()
        ops_count = 0
        cost_cents_used = 0
        
        # Create budget object
        budget = Budget(ms=budget_ms, ops=budget_ops, cost_cents=budget_cost_cents)
        
        run = {
            "run_id": run_id,
            "status": "running",
            "started_at": datetime.utcnow(),
            "logs": [f"start agent={plan['agent']} objective={plan['objective']}"],
            "finished_at": None,
            "artifacts": {},
            "budget_ms": budget_ms,
            "budget_ops": budget_ops,
            "budget_cost_cents": budget_cost_cents,
            "ops_count": 0,
            "cost_cents_used": 0,
        }
        self.run_store[run_id] = run
        
        # Check if actions are allowed
        if not allow_actions and not plan.get("dry_run", True):
            run.update({
                "status": "failed",
                "finished_at": datetime.utcnow(),
                "logs": run["logs"] + ["error: Actions not allowed (allow_actions=false)"],
            })
            return run
        
        # Emit run_started event
        if self.event_bus:
            self.event_bus.publish_sync(AgentEvent(
                event_type="run_started",
                run_id=run_id,
                agent=plan["agent"],
                timestamp=time.time(),
                data={
                    "objective": plan["objective"],
                    "plan": plan,
                }
            ))
        
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
            # Create execution context with budget tracking
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            budget_status = budget.is_exceeded(
                elapsed_ms=elapsed_ms,
                ops_used=ops_count,
                cost_cents_used=cost_cents_used
            )
            
            if budget_status["exceeded"]:
                raise RuntimeError(
                    f"Budget exceeded before execution: {budget_status}"
                )
            
            # Execute handler with budget tracking callback
            result = handler(plan)
            
            # Update ops count (handler should track operations)
            ops_count = result.get("ops_count", ops_count) if isinstance(result, dict) else ops_count
            cost_cents_used = result.get("cost_cents_used", cost_cents_used) if isinstance(result, dict) else cost_cents_used
            run["ops_count"] = ops_count
            run["cost_cents_used"] = cost_cents_used
            
            # Check budget after execution
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            budget_status = budget.is_exceeded(
                elapsed_ms=elapsed_ms,
                ops_used=ops_count,
                cost_cents_used=cost_cents_used
            )
            
            if budget_status["exceeded"]:
                exceeded_details = []
                if budget_status.get("time_exceeded"):
                    exceeded_details.append(f"time: {elapsed_ms}ms > {budget_ms}ms")
                if budget_status.get("ops_exceeded"):
                    exceeded_details.append(f"ops: {ops_count} > {budget_ops}")
                if budget_status.get("cost_exceeded"):
                    exceeded_details.append(f"cost: {cost_cents_used}¢ > {budget_cost_cents}¢")
                
                run["logs"].append(
                    f"warning: Budget exceeded during execution: {', '.join(exceeded_details)}"
                )
            
            duration_ms = elapsed_ms
            
            run.update({
                "status": "succeeded",
                "finished_at": datetime.utcnow(),
                "artifacts": result or {},
            })
            
            # Emit run_finished event
            if self.event_bus:
                self.event_bus.publish_sync(AgentEvent(
                    event_type="run_finished",
                    run_id=run_id,
                    agent=plan["agent"],
                    timestamp=time.time(),
                    data={
                        "status": "succeeded",
                        "artifacts": result or {},
                        "duration_ms": duration_ms,
                    }
                ))
            
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
            
            # Emit run_failed event
            if self.event_bus:
                self.event_bus.publish_sync(AgentEvent(
                    event_type="run_failed",
                    run_id=run_id,
                    agent=plan["agent"],
                    timestamp=time.time(),
                    data={
                        "status": "failed",
                        "error": error_msg,
                        "duration_ms": duration_ms,
                    }
                ))
            
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
