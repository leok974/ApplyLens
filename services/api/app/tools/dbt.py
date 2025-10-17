"""dbt tool wrapper for agent system.

Phase-1: Provides deterministic mock responses for testing.
Phase-2: Can integrate with dbt CLI or dbt Cloud API.
"""

from __future__ import annotations

import time

from ..schemas.tools import DbtRunResult


class _MockDbtProvider:
    """Mock dbt provider for testing."""
    
    def run(
        self, 
        target: str = "prod", 
        models: str | None = None
    ) -> DbtRunResult:
        """Run dbt models (mock).
        
        Args:
            target: dbt target environment
            models: Model selector (e.g., "tag:daily")
            
        Returns:
            Mock run result
        """
        t0 = time.time()
        time.sleep(0.01)  # Simulate some work
        elapsed = time.time() - t0
        
        return DbtRunResult(
            success=True,
            elapsed_sec=elapsed,
            artifacts_path="target/run_results.json"
        )


class DbtTool:
    """dbt operations tool.
    
    Provides typed interface for dbt operations.
    Uses provider factory to get mock or real implementation.
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
        from ..providers.factory import provider_factory
        provider = provider_factory.dbt()
        return provider.run(target=target, models=models)
