"""
Security event bus for real-time notifications.

Provides a simple pub/sub system for broadcasting security events
(e.g., high-risk email detected) to connected clients via SSE.
"""
import asyncio
from typing import Any, Dict, Set


class SecurityEventBus:
    """
    Simple in-memory pub/sub event bus for security events.
    
    Usage:
        # Subscribe to events
        queue = BUS.subscribe()
        
        # Publish event
        await BUS.publish({"type": "high_risk", "email_id": "123", "score": 85})
        
        # Unsubscribe
        BUS.unsubscribe(queue)
    """
    
    def __init__(self):
        self._subs: Set[asyncio.Queue] = set()
    
    def subscribe(self) -> asyncio.Queue:
        """
        Subscribe to security events.
        Returns a queue that will receive all published events.
        """
        q: asyncio.Queue = asyncio.Queue()
        self._subs.add(q)
        return q
    
    def unsubscribe(self, q: asyncio.Queue):
        """Unsubscribe from security events."""
        self._subs.discard(q)
    
    async def publish(self, event: Dict[str, Any]):
        """
        Publish an event to all subscribers.
        
        Args:
            event: Event data dictionary (must be JSON-serializable)
        """
        for q in list(self._subs):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Skip if queue is full (slow consumer)
                pass
            except Exception:
                # Silently ignore errors
                pass


# Global event bus instance
BUS = SecurityEventBus()
