"""Gmail tool wrapper for agent system.

Phase-1: Provides deterministic mock responses for testing.
Phase-2: Can integrate with real Gmail API via oauth_google module.
"""

from __future__ import annotations

from ..schemas.tools import GmailMessage, GmailSearchResponse


class _MockGmailProvider:
    """Mock Gmail provider for testing."""
    
    def search_recent(self, days: int = 7) -> GmailSearchResponse:
        """Search for recent emails (mock).
        
        Args:
            days: Number of days to look back
            
        Returns:
            Search response with mock messages
        """
        messages = [
            GmailMessage(
                id="m1",
                thread_id="t1",
                subject="Job Offer - Senior Engineer",
                from_addr="hr@example.com",
                received_at="2025-10-15T12:00:00Z"
            )
        ]
        return GmailSearchResponse(messages=messages)


class GmailTool:
    """Gmail operations tool.
    
    Provides typed interface for Gmail operations.
    Uses provider factory to get mock or real implementation.
    """
    
    def __init__(self, allow_actions: bool = False):
        """Initialize Gmail tool.
        
        Args:
            allow_actions: Whether to allow write operations (default: False for safety)
        """
        self.allow_actions = allow_actions
    
    def search_recent(self, days: int = 7) -> GmailSearchResponse:
        """Search for recent emails.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Search response with matching messages
        """
        from ..providers.factory import provider_factory
        provider = provider_factory.gmail()
        return provider.search_recent(days=days)
