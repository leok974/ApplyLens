"""dbt tool wrapper for agent system.

Phase-1: Provides deterministic mock responses for testing.
Phase-2: Can integrate with dbt CLI or dbt Cloud API.
"""

from __future__ import annotations

import time

from ..schemas.tools import DbtRunResult


class DbtTool:
    """dbt operations tool.
    
    Provides typed interface for dbt operations.
    Phase-1 returns mock data for portability and golden testing.
    """
    
    def __init__(self, allow_actions: bool = False):
        """Initialize dbt tool.
        
        Args:
            allow_actions: Whether to allow actual runs (default: False for safety)
        """
        self.allow_actions = allow_actions
    
    def run(
        self, 
        target: str = "prod", 
        models: str | None = None
    ) -> DbtRunResult:
        """Run dbt models.
        
        Args:
            target: dbt target environment
            models: Model selector (e.g., "tag:daily")
            
        Returns:
            Run result with success status and timing
        """
        # Phase-1: Simulate execution time and return mock result
        t0 = time.time()
        time.sleep(0.01)  # Simulate some work
        elapsed = time.time() - t0
        
        return DbtRunResult(
            success=True,
            elapsed_sec=elapsed,
            artifacts_path="target/run_results.json"
        )
