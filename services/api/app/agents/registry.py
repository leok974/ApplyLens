"""Agent registry - manages available agents."""

from __future__ import annotations

from typing import Callable, Dict


class AgentRegistry:
    """Registry for available agents.
    
    Provides:
    - Registration of agent handlers
    - Lookup by name
    - Listing all registered agents
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._agents: Dict[str, Callable] = {}
    
    def register(self, name: str, handler: Callable):
        """Register an agent handler.
        
        Args:
            name: Unique agent identifier
            handler: Callable that executes the agent
        """
        self._agents[name] = handler
    
    def get(self, name: str) -> Callable:
        """Get an agent handler by name.
        
        Args:
            name: Agent identifier
            
        Returns:
            Agent handler callable
            
        Raises:
            KeyError: If agent not found
        """
        if name not in self._agents:
            raise KeyError(f"unknown agent: {name}")
        return self._agents[name]
    
    def list(self) -> list[str]:
        """List all registered agent names.
        
        Returns:
            Sorted list of agent names
        """
        return sorted(self._agents.keys())
