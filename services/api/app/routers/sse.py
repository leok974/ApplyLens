"""
SSE Notifications - Phase 5.4 PR4

Server-Sent Events for real-time incident updates.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.models_incident import Incident

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sse", tags=["sse"])


class SSEPublisher:
    """
    Simple in-memory SSE publisher.

    For production, replace with Redis/NATS for multi-worker support.
    """

    def __init__(self):
        self.subscribers: Dict[str, asyncio.Queue] = {}
        self.event_counter = 0

    async def publish(self, event: Dict[str, Any]):
        """
        Publish event to all subscribers.

        Args:
            event: Event data with type, data, id
        """
        self.event_counter += 1
        event_with_id = {
            **event,
            "id": self.event_counter,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(
            f"Publishing SSE event: {event['event']} (subscribers: {len(self.subscribers)})"
        )

        # Send to all subscribers
        dead_subscribers = []
        for subscriber_id, queue in self.subscribers.items():
            try:
                await queue.put(event_with_id)
            except Exception as e:
                logger.warning(f"Failed to send to subscriber {subscriber_id}: {e}")
                dead_subscribers.append(subscriber_id)

        # Clean up dead subscribers
        for subscriber_id in dead_subscribers:
            self.subscribers.pop(subscriber_id, None)

    async def subscribe(self, subscriber_id: str) -> asyncio.Queue:
        """
        Subscribe to events.

        Returns:
            Queue for receiving events
        """
        queue = asyncio.Queue(maxsize=100)
        self.subscribers[subscriber_id] = queue
        logger.info(
            f"New SSE subscriber: {subscriber_id} (total: {len(self.subscribers)})"
        )
        return queue

    def unsubscribe(self, subscriber_id: str):
        """Unsubscribe from events."""
        self.subscribers.pop(subscriber_id, None)
        logger.info(
            f"SSE subscriber left: {subscriber_id} (remaining: {len(self.subscribers)})"
        )


# Global publisher (in production, use Redis/NATS)
_publisher = SSEPublisher()


def get_publisher() -> SSEPublisher:
    """Get SSE publisher instance."""
    return _publisher


async def event_generator(
    subscriber_id: str,
    queue: asyncio.Queue,
    request: Request,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for a client.

    Yields:
        SSE-formatted event strings
    """
    try:
        # Send initial connection event
        yield f"event: connected\ndata: {json.dumps({'subscriber_id': subscriber_id})}\n\n"

        # Send heartbeat every 30 seconds
        heartbeat_task = asyncio.create_task(_heartbeat(queue))

        # Stream events
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info(f"Client {subscriber_id} disconnected")
                break

            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(queue.get(), timeout=1.0)

                # Format as SSE
                event_type = event.get("event", "message")
                data = json.dumps(event.get("data", {}))
                event_id = event.get("id", "")

                sse_message = f"event: {event_type}\ndata: {data}\nid: {event_id}\n\n"
                yield sse_message

            except asyncio.TimeoutError:
                # No event, continue to check disconnect
                continue

    except Exception as e:
        logger.exception(f"Error in event generator: {e}")
    finally:
        # Cleanup
        heartbeat_task.cancel()
        get_publisher().unsubscribe(subscriber_id)


async def _heartbeat(queue: asyncio.Queue):
    """Send periodic heartbeat to keep connection alive."""
    while True:
        await asyncio.sleep(30)
        try:
            await queue.put(
                {
                    "event": "heartbeat",
                    "data": {"timestamp": datetime.utcnow().isoformat()},
                }
            )
        except Exception:
            break


@router.get("/events")
async def sse_events(request: Request):
    """
    SSE endpoint for real-time incident updates.

    Events:
    - incident_created: New incident created
    - incident_updated: Incident state changed
    - action_executed: Remediation action executed

    Usage:
        const eventSource = new EventSource('/api/sse/events');
        eventSource.addEventListener('incident_created', (e) => {
            const incident = JSON.parse(e.data);
            console.log('New incident:', incident);
        });
    """
    # Generate unique subscriber ID
    import uuid

    subscriber_id = str(uuid.uuid4())

    # Subscribe to events
    publisher = get_publisher()
    queue = await publisher.subscribe(subscriber_id)

    # Return streaming response
    return StreamingResponse(
        event_generator(subscriber_id, queue, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


async def publish_incident_created(incident: Incident):
    """Publish incident_created event."""
    publisher = get_publisher()
    await publisher.publish(
        {
            "event": "incident_created",
            "data": {
                "id": incident.id,
                "kind": incident.kind,
                "severity": incident.severity,
                "status": incident.status,
                "summary": incident.summary,
                "created_at": incident.created_at.isoformat()
                if incident.created_at
                else None,
            },
        }
    )


async def publish_incident_updated(incident: Incident, change_type: str):
    """Publish incident_updated event."""
    publisher = get_publisher()
    await publisher.publish(
        {
            "event": "incident_updated",
            "data": {
                "id": incident.id,
                "change_type": change_type,  # e.g., "acknowledged", "mitigated"
                "status": incident.status,
                "updated_at": datetime.utcnow().isoformat(),
            },
        }
    )


async def publish_action_executed(incident_id: int, action_type: str, status: str):
    """Publish action_executed event."""
    publisher = get_publisher()
    await publisher.publish(
        {
            "event": "action_executed",
            "data": {
                "incident_id": incident_id,
                "action_type": action_type,
                "status": status,
                "executed_at": datetime.utcnow().isoformat(),
            },
        }
    )
