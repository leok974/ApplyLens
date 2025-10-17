"""Server-Sent Events (SSE) endpoint for real-time agent run updates.

Provides /agents/events endpoint for clients to receive live updates about
agent executions via SSE protocol.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..events import get_event_bus

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/events")
async def stream_agent_events():
    """Stream real-time agent run events via Server-Sent Events.
    
    Returns:
        StreamingResponse with text/event-stream content type
        
    Example:
        ```javascript
        const eventSource = new EventSource('/agents/events');
        
        eventSource.addEventListener('run_started', (e) => {
            const data = JSON.parse(e.data);
            console.log(`Run ${data.run_id} started`);
        });
        
        eventSource.addEventListener('run_log', (e) => {
            const data = JSON.parse(e.data);
            console.log(`Log: ${data.message}`);
        });
        
        eventSource.addEventListener('run_finished', (e) => {
            const data = JSON.parse(e.data);
            console.log(`Run ${data.run_id} finished: ${data.status}`);
        });
        ```
    
    Event Types:
        - run_started: Run initiated (data: run_id, agent, objective, plan)
        - run_log: Log message emitted (data: run_id, message, level)
        - run_finished: Run completed successfully (data: run_id, status, artifacts, duration_ms)
        - run_failed: Run failed with error (data: run_id, status, error, duration_ms)
    """
    event_bus = get_event_bus()
    
    async def event_generator():
        """Generate SSE messages from event bus."""
        async for event in event_bus.subscribe():
            yield event.to_sse()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
