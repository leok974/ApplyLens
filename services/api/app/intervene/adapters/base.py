"""
Base adapter interface for issue tracking systems.

Defines the contract that all issue adapters must implement.
Supports GitHub, GitLab, Jira, and custom systems.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class IssueAttachment:
    """Attachment to include with issue (logs, artifacts, screenshots)."""
    name: str
    content: bytes
    content_type: str


@dataclass
class IssueCreateRequest:
    """Request to create a new issue."""
    title: str
    body: str
    labels: List[str]
    priority: Optional[str] = None  # P0-P4, High/Medium/Low, etc.
    assignee: Optional[str] = None
    attachments: List[IssueAttachment] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


@dataclass
class IssueCreateResponse:
    """Response from creating an issue."""
    success: bool
    issue_id: str
    issue_url: str
    error: Optional[str] = None


class IssueAdapter(ABC):
    """
    Base adapter for issue tracking systems.
    
    All external API calls should be done through adapters
    so they can be mocked in tests and swapped in production.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter with configuration.
        
        Args:
            config: Provider-specific configuration
                - base_url: API endpoint
                - token: Authentication token
                - project/repo: Target project/repository
                - etc.
        """
        self.config = config
    
    @abstractmethod
    def create_issue(self, request: IssueCreateRequest) -> IssueCreateResponse:
        """
        Create a new issue.
        
        Args:
            request: Issue creation request
            
        Returns:
            Response with issue URL and ID
            
        Raises:
            IssueAdapterError: If creation fails
        """
        pass
    
    @abstractmethod
    def update_issue(
        self,
        issue_id: str,
        comment: Optional[str] = None,
        labels: Optional[List[str]] = None,
        status: Optional[str] = None
    ) -> bool:
        """
        Update an existing issue.
        
        Args:
            issue_id: Issue identifier
            comment: Comment to add
            labels: Labels to set/add
            status: Status to transition to
            
        Returns:
            True if update succeeded
        """
        pass
    
    @abstractmethod
    def close_issue(self, issue_id: str, comment: Optional[str] = None) -> bool:
        """
        Close an issue.
        
        Args:
            issue_id: Issue identifier
            comment: Optional closing comment
            
        Returns:
            True if close succeeded
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate adapter configuration.
        
        Returns:
            True if configuration is valid
        """
        required_keys = self.get_required_config_keys()
        return all(key in self.config for key in required_keys)
    
    @abstractmethod
    def get_required_config_keys(self) -> List[str]:
        """
        Get list of required configuration keys.
        
        Returns:
            List of required config key names
        """
        pass
    
    def test_connection(self) -> bool:
        """
        Test connectivity to issue tracking system.
        
        Returns:
            True if connection successful
        """
        try:
            # Override in subclass with provider-specific health check
            return True
        except Exception:
            return False


class IssueAdapterError(Exception):
    """Exception raised by issue adapters."""
    pass


class IssueAdapterFactory:
    """Factory for creating issue adapters based on provider."""
    
    _adapters = {}
    
    @classmethod
    def register(cls, provider: str, adapter_class: type):
        """Register an adapter class for a provider."""
        cls._adapters[provider] = adapter_class
    
    @classmethod
    def create(cls, provider: str, config: Dict[str, Any]) -> IssueAdapter:
        """
        Create adapter instance for provider.
        
        Args:
            provider: Provider name (github, gitlab, jira, mock)
            config: Provider-specific configuration
            
        Returns:
            Adapter instance
            
        Raises:
            ValueError: If provider not registered
        """
        if provider not in cls._adapters:
            raise ValueError(f"Unknown issue provider: {provider}")
        
        adapter_class = cls._adapters[provider]
        return adapter_class(config)
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """Get list of registered providers."""
        return list(cls._adapters.keys())
