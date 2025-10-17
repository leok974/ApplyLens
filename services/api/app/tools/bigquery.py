"""BigQuery tool wrapper for agent system.

Phase-1: Provides deterministic mock responses for testing.
Phase-2: Can integrate with real BigQuery client.
"""

from __future__ import annotations

from typing import Any

from ..schemas.tools import BQQueryResult


class _MockBQProvider:
    """Mock BigQuery provider for testing."""
    
    def query(self, sql: str) -> BQQueryResult:
        """Execute a SQL query (mock).
        
        Args:
            sql: SQL query to execute
            
        Returns:
            Query result with mock rows and statistics
        """
        rows = [
            {"day": "2025-10-15", "emails": 42},
            {"day": "2025-10-16", "emails": 38},
        ]
        stats = {
            "bytes_processed": 0,
            "bytes_billed": 0,
            "cached": True,
            "execution_time_ms": 123,
        }
        return BQQueryResult(rows=rows, stats=stats)
    
    def query_rows(self, sql: str) -> list[dict[str, Any]]:
        """Execute query and return only rows (mock)."""
        return self.query(sql).rows
    
    def query_scalar(self, sql: str) -> Any:
        """Execute query expecting single scalar value (mock)."""
        rows = self.query_rows(sql)
        if not rows:
            return None
        return next(iter(rows[0].values()))


class BigQueryTool:
    """BigQuery operations tool.
    
    Provides typed interface for BigQuery operations.
    Uses provider factory to get mock or real implementation.
    """
    
    def __init__(self, allow_actions: bool = False):
        """Initialize BigQuery tool.
        
        Args:
            allow_actions: Whether to allow write operations (default: False for safety)
        """
        self.allow_actions = allow_actions
    
    def query(self, sql: str) -> BQQueryResult:
        """Execute a SQL query.
        
        Args:
            sql: SQL query to execute
            
        Returns:
            Query result with rows and statistics
        """
        from ..providers.factory import provider_factory
        provider = provider_factory.bigquery()
        return provider.query(sql)
