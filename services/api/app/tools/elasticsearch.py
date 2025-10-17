"""Elasticsearch tool wrapper for agent system.

Phase-1: Provides deterministic mock responses for testing.
Phase-2: Can integrate with real Elasticsearch client.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from ..schemas.tools import ESSearchHit, ESSearchResponse


def require_env(key: str, default: str | None = None) -> str:
    """Get required environment variable with optional default.
    
    Args:
        key: Environment variable name
        default: Default value if not set
        
    Returns:
        Environment variable value
    """
    return os.getenv(key, default or "")


class _MockESProvider:
    """Mock Elasticsearch provider for testing."""
    
    def search(self, query: dict[str, Any], index: str | None = None) -> ESSearchResponse:
        """Search documents (mock).
        
        Args:
            query: Elasticsearch query DSL
            index: Index to search
            
        Returns:
            Mock search response
        """
        hits = [
            ESSearchHit(
                id="email1",
                score=1.0,
                source={
                    "subject": "Job Application - Software Engineer",
                    "from": "applicant@example.com",
                    "received_at": "2025-10-15T10:00:00Z",
                    "body_preview": "I am writing to apply..."
                }
            ),
            ESSearchHit(
                id="email2",
                score=0.95,
                source={
                    "subject": "Interview Invitation",
                    "from": "hr@company.com",
                    "received_at": "2025-10-16T14:30:00Z",
                    "body_preview": "We would like to invite you..."
                }
            )
        ]
        return ESSearchResponse(hits=hits)
    
    def aggregate_daily(self, index: str | None = None, days: int = 7) -> list[dict[str, Any]]:
        """Aggregate document counts by day (mock)."""
        return [
            {"day": "2025-10-15", "emails": 42},
            {"day": "2025-10-16", "emails": 38},
        ]
    
    def latest_event_ts(self, index: str | None = None) -> str | None:
        """Get timestamp of most recent document (mock)."""
        return "2025-10-17T12:00:00Z"


class ESTool:
    """Elasticsearch operations tool.
    
    Provides typed interface for Elasticsearch operations.
    Uses provider factory to get mock or real implementation.
    """
    
    def __init__(
        self, 
        host: str | None = None, 
        index: str | None = None,
        allow_actions: bool = False
    ):
        """Initialize Elasticsearch tool.
        
        Args:
            host: Elasticsearch host URL
            index: Default index name
            allow_actions: Whether to allow write operations (default: False for safety)
        """
        self.host = host or require_env("ES_HOST", default="http://elasticsearch:9200")
        self.index = index or require_env("ES_INDEX", default="emails")
        self.allow_actions = allow_actions
    
    def search(self, query: Dict[str, Any]) -> ESSearchResponse:
        """Search documents.
        
        Args:
            query: Elasticsearch query DSL
            
        Returns:
            Search response with hits
        """
        from ..providers.factory import provider_factory
        provider = provider_factory.es()
        return provider.search(query, index=self.index)
