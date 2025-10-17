"""BigQuery tool wrapper for agent system.

Phase-1: Provides deterministic mock responses for testing.
Phase-2: Can integrate with real BigQuery client.
"""

from __future__ import annotations

from ..schemas.tools import BQQueryResult


class BigQueryTool:
    """BigQuery operations tool.
    
    Provides typed interface for BigQuery operations.
    Phase-1 returns mock data for portability and golden testing.
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
        # Phase-1: Return deterministic mock data for golden tests
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
