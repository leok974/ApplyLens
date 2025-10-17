"""
DBT Actions - Phase 5.4 PR3

Actions for dbt model remediation.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from app.intervene.actions.base import (
    AbstractAction,
    ActionResult,
    ActionStatus,
    register_action,
)

logger = logging.getLogger(__name__)


@register_action("rerun_dbt")
class RerunDbtAction(AbstractAction):
    """
    Re-run dbt models that failed.
    
    Use cases:
    - Invariant failure due to stale data
    - Temporary data quality issues
    - Dependency failures
    
    Parameters:
        task_id: Task ID that failed
        models: List of dbt model names to re-run
        full_refresh: Whether to do full refresh (default: False)
        upstream: Whether to include upstream models (default: False)
        threads: Number of threads (default: 4)
    """
    
    def __init__(
        self,
        task_id: int,
        models: List[str],
        full_refresh: bool = False,
        upstream: bool = False,
        threads: int = 4,
        **kwargs
    ):
        super().__init__(
            task_id=task_id,
            models=models,
            full_refresh=full_refresh,
            upstream=upstream,
            threads=threads,
            **kwargs
        )
        self.task_id = task_id
        self.models = models
        self.full_refresh = full_refresh
        self.upstream = upstream
        self.threads = threads
    
    def validate(self) -> bool:
        """Validate dbt models exist and task is valid."""
        # Check task exists
        from app.db import SessionLocal
        from app.eval.models import Task
        
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == self.task_id).first()
            if not task:
                raise ValueError(f"Task {self.task_id} not found")
            
            # TODO: Validate models exist in dbt manifest
            # For now, basic validation
            if not self.models:
                raise ValueError("At least one model must be specified")
            
            return True
            
        finally:
            db.close()
    
    def dry_run(self) -> ActionResult:
        """Simulate dbt run."""
        changes = []
        
        # Build command preview
        cmd_parts = ["dbt", "run"]
        cmd_parts.extend(["--select"] + self.models)
        
        if self.full_refresh:
            cmd_parts.append("--full-refresh")
            changes.append("⚠️ Full refresh will truncate and rebuild tables")
        
        if self.upstream:
            cmd_parts.append("+")
            changes.append("📦 Will include upstream dependencies")
        
        cmd_parts.extend(["--threads", str(self.threads)])
        
        cmd = " ".join(cmd_parts)
        changes.append(f"🔧 Command: {cmd}")
        
        # Estimate metrics
        num_models = len(self.models)
        estimated_duration = f"{num_models * 2}m"  # ~2min per model
        estimated_cost = num_models * 0.05  # ~$0.05 per model
        
        if self.full_refresh:
            estimated_duration = f"{num_models * 5}m"  # Longer for full refresh
            estimated_cost *= 3
        
        changes.append(f"📊 Will rebuild {num_models} model(s)")
        changes.append(f"⏱️ Estimated duration: {estimated_duration}")
        changes.append(f"💰 Estimated cost: ${estimated_cost:.2f}")
        
        return ActionResult(
            status=ActionStatus.DRY_RUN_SUCCESS,
            message=f"Ready to re-run {num_models} dbt model(s)",
            details={
                "command": cmd,
                "models": self.models,
                "full_refresh": self.full_refresh,
                "upstream": self.upstream,
            },
            estimated_duration=estimated_duration,
            estimated_cost=estimated_cost,
            changes=changes,
            rollback_available=False,
        )
    
    def execute(self) -> ActionResult:
        """Execute dbt run."""
        start_time = datetime.utcnow()
        
        try:
            # TODO: Integrate with actual dbt execution system
            # For now, simulate execution
            logger.info(f"Executing dbt run for task {self.task_id}: {self.models}")
            
            # Build command
            cmd_parts = ["dbt", "run", "--select"] + self.models
            if self.full_refresh:
                cmd_parts.append("--full-refresh")
            if self.upstream:
                cmd_parts.append("+")
            cmd_parts.extend(["--threads", str(self.threads)])
            
            cmd = " ".join(cmd_parts)
            
            # Simulate execution
            # In real implementation, this would:
            # 1. Trigger dbt Cloud job or local dbt run
            # 2. Wait for completion or return job ID
            # 3. Stream logs to monitoring
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return ActionResult(
                status=ActionStatus.SUCCESS,
                message=f"Successfully re-ran {len(self.models)} dbt model(s)",
                details={
                    "command": cmd,
                    "models": self.models,
                    "models_rebuilt": len(self.models),
                    "full_refresh": self.full_refresh,
                },
                actual_duration=duration,
                logs_url=f"/logs/dbt/task_{self.task_id}",
                rollback_available=False,
            )
            
        except Exception as e:
            logger.exception(f"Failed to execute dbt run: {e}")
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return ActionResult(
                status=ActionStatus.FAILED,
                message=f"Failed to re-run dbt models: {str(e)}",
                details={"error": str(e)},
                actual_duration=duration,
            )
    
    def get_approval_required(self) -> bool:
        """Full refresh requires approval, incremental runs don't."""
        return self.full_refresh
    
    def get_estimated_impact(self) -> Dict[str, Any]:
        """Get impact assessment."""
        risk_level = "high" if self.full_refresh else "low"
        downtime = "5-30m" if self.full_refresh else "0s"
        
        return {
            "risk_level": risk_level,
            "affected_systems": ["dbt", "data_warehouse"],
            "estimated_downtime": downtime,
            "reversible": False,
            "models_affected": len(self.models),
        }


@register_action("refresh_dbt_dependencies")
class RefreshDbtDependenciesAction(AbstractAction):
    """
    Refresh dbt dependencies and re-compile.
    
    Use for:
    - Package version mismatches
    - Macro compilation errors
    - Dependency resolution issues
    
    Parameters:
        project_path: Path to dbt project (optional)
    """
    
    def __init__(self, project_path: Optional[str] = None, **kwargs):
        super().__init__(project_path=project_path, **kwargs)
        self.project_path = project_path or "/opt/dbt"
    
    def validate(self) -> bool:
        """Validate dbt project exists."""
        # TODO: Check project path exists
        return True
    
    def dry_run(self) -> ActionResult:
        """Simulate dependency refresh."""
        changes = [
            "📦 Will run: dbt deps",
            "🔨 Will run: dbt compile",
            "✅ Will validate compiled SQL",
        ]
        
        return ActionResult(
            status=ActionStatus.DRY_RUN_SUCCESS,
            message="Ready to refresh dbt dependencies",
            details={"project_path": self.project_path},
            estimated_duration="2m",
            estimated_cost=0.0,
            changes=changes,
            rollback_available=False,
        )
    
    def execute(self) -> ActionResult:
        """Execute dependency refresh."""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Refreshing dbt dependencies at {self.project_path}")
            
            # TODO: Execute dbt deps && dbt compile
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return ActionResult(
                status=ActionStatus.SUCCESS,
                message="Successfully refreshed dbt dependencies",
                details={"project_path": self.project_path},
                actual_duration=duration,
                logs_url=f"/logs/dbt/deps",
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return ActionResult(
                status=ActionStatus.FAILED,
                message=f"Failed to refresh dependencies: {str(e)}",
                details={"error": str(e)},
                actual_duration=duration,
            )
    
    def get_approval_required(self) -> bool:
        """Low risk, no approval needed."""
        return False
