"""Event bus for broadcasting agent run updates in real-time.

Implements an AsyncIO-based pub/sub system for Server-Sent Events (SSE).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict


@dataclass
class AgentEvent:
    """Agent run event for SSE streaming.
    
    Attributes:
        event_type: Type of event (run_started, run_log, run_finished, run_failed)
        run_id: Unique run identifier
        agent: Agent name
        timestamp: Unix timestamp (seconds)
        data: Event-specific data (varies by type)
    """
    event_type: str
    run_id: str
    agent: str
    timestamp: float
    data: Dict[str, Any]
    
    def to_sse(self) -> str:
        """Format as Server-Sent Event message.
        
        Returns:
            SSE-formatted string with event, id, and data fields
        """
        import json
        
        # SSE format: event, id, data (one per line, double newline at end)
        data_dict = {
            'run_id': self.run_id,
            'agent': self.agent,
            'timestamp': self.timestamp,
            **self.data
        }
        lines = [
            f"event: {self.event_type}",
            f"id: {self.run_id}",
            f"data: {json.dumps(data_dict)}",
            "",  # Double newline required by SSE spec
        ]
        return "\n".join(lines) + "\n"


class EventBus:
    """AsyncIO event bus for broadcasting agent run events.
    
    Supports multiple subscribers receiving real-time updates via Server-Sent Events.
    Thread-safe via asyncio.Queue per subscriber.
    """
    
    def __init__(self):
        """Initialize event bus with empty subscriber list."""
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()
    
    async def subscribe(self) -> AsyncGenerator[AgentEvent, None]:
        """Subscribe to agent events.
        
        Yields:
            AgentEvent instances as they are published
        """
        queue: asyncio.Queue = asyncio.Queue()
        
        async with self._lock:
            self._subscribers.append(queue)
        
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            # Cleanup on client disconnect
            async with self._lock:
                if queue in self._subscribers:
                    self._subscribers.remove(queue)
    
    async def publish(self, event: AgentEvent) -> None:
        """Publish event to all subscribers.
        
        Args:
            event: Agent event to broadcast
        """
        async with self._lock:
            # Send to all active subscribers
            for queue in self._subscribers:
                try:
                    await queue.put(event)
                except Exception:
                    # Skip failed subscribers (likely disconnected)
                    pass
    
    def publish_sync(self, event: AgentEvent) -> None:
        """Publish event from synchronous code.
        
        Creates task to publish event asynchronously. Safe to call from
        non-async contexts (like executor).
        
        Args:
            event: Agent event to broadcast
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.publish(event))
            else:
                # No event loop running, skip (likely in tests)
                pass
        except RuntimeError:
            # No event loop, skip (likely in tests or sync context)
            pass
    
    @property
    def subscriber_count(self) -> int:
        """Get number of active subscribers.
        
        Returns:
            Number of connected clients
        """
        return len(self._subscribers)


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get global event bus instance.
    
    Returns:
        EventBus singleton
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def set_event_bus(bus: EventBus | None) -> None:
    """Set global event bus instance (for testing).
    
    Args:
        bus: EventBus instance or None to reset
    """
    global _event_bus
    _event_bus = bus
