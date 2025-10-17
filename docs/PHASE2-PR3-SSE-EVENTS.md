# Phase 2 PR3: Server-Sent Events (SSE) for Real-Time Agent Updates

**Date**: January 2025  
**Status**: ✅ Complete  
**Dependencies**: Phase 2 PR1 (Providers), Phase 2 PR2 (Audit & Metrics)

## What Was Built

This PR adds real-time streaming of agent execution updates via Server-Sent Events (SSE), enabling clients to receive live updates as agents run.

### 1. Event Bus System

**File**: `services/api/app/events/bus.py`

AsyncIO-based pub/sub system for broadcasting agent events:

```python
@dataclass
class AgentEvent:
    """Agent run event for SSE streaming."""
    event_type: str  # run_started, run_log, run_finished, run_failed
    run_id: str
    agent: str
    timestamp: float  # Unix timestamp
    data: Dict[str, Any]  # Event-specific payload
    
    def to_sse(self) -> str:
        """Format as Server-Sent Event message."""
        # Returns SSE-formatted string: event, id, data fields
```

```python
class EventBus:
    """AsyncIO event bus for broadcasting agent run events."""
    
    async def subscribe(self) -> AsyncGenerator[AgentEvent, None]:
        """Subscribe to agent events (async generator)."""
    
    async def publish(self, event: AgentEvent) -> None:
        """Publish event to all subscribers (async)."""
    
    def publish_sync(self, event: AgentEvent) -> None:
        """Publish event from synchronous code (safe for executor)."""
    
    @property
    def subscriber_count(self) -> int:
        """Get number of active subscribers."""
```

**Key Features**:
- **AsyncIO-based**: Uses `asyncio.Queue` per subscriber for thread-safe delivery
- **Automatic cleanup**: Removes disconnected subscribers
- **Sync-safe**: `publish_sync()` creates task for async publish from sync code
- **SSE formatting**: `to_sse()` generates spec-compliant event stream messages

### 2. SSE Endpoint

**File**: `services/api/app/routers/agents_events.py`

FastAPI endpoint for streaming agent events:

```python
@router.get("/agents/events")
async def stream_agent_events():
    """Stream real-time agent run events via Server-Sent Events."""
    
    async def event_generator():
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
```

**Event Types**:
- `run_started`: Run initiated (data: objective, plan)
- `run_log`: Log message emitted (data: message, level) *[future PR]*
- `run_finished`: Run completed successfully (data: status, artifacts, duration_ms)
- `run_failed`: Run failed with error (data: status, error, duration_ms)

### 3. Executor Event Emission

**File**: `services/api/app/agents/executor.py`

Updated executor to emit events during run lifecycle:

**Lifecycle with Events**:
1. `execute()` called with plan
2. **Emit `run_started` event** → notify subscribers
3. `auditor.log_start()` → database audit trail
4. Handler executes
5. **Emit `run_finished` or `run_failed` event** → notify subscribers
6. `auditor.log_finish()` → database audit trail
7. `record_agent_run()` → Prometheus metrics
8. Return run record

**Integration**:
```python
class Executor:
    def __init__(
        self, 
        run_store, 
        auditor=None,
        event_bus_enabled=True  # NEW: Toggle events
    ):
        self.event_bus_enabled = event_bus_enabled
        if event_bus_enabled:
            self.event_bus = get_event_bus()
```

**Emit Events**:
```python
# On start
if self.event_bus:
    self.event_bus.publish_sync(AgentEvent(
        event_type="run_started",
        run_id=run_id,
        agent=plan["agent"],
        timestamp=time.time(),
        data={"objective": plan["objective"], "plan": plan}
    ))

# On success
if self.event_bus:
    self.event_bus.publish_sync(AgentEvent(
        event_type="run_finished",
        run_id=run_id,
        agent=plan["agent"],
        timestamp=time.time(),
        data={
            "status": "succeeded",
            "artifacts": result or {},
            "duration_ms": duration_ms
        }
    ))

# On failure
if self.event_bus:
    self.event_bus.publish_sync(AgentEvent(
        event_type="run_failed",
        ...
        data={"status": "failed", "error": error_msg, "duration_ms": duration_ms}
    ))
```

### 4. Main App Integration

**File**: `services/api/app/main.py`

Wired SSE router to FastAPI app:

```python
from .routers.agents import router as agents_router
from .routers.agents_events import router as agents_events_router

app.include_router(agents_router)
app.include_router(agents_events_router)  # NEW: SSE endpoint
```

---

## Design Principles

### 1. **Real-Time by Default**

- All agent runs automatically broadcast events
- Clients can subscribe to `/agents/events` for live updates
- No polling required - events pushed immediately

### 2. **Standards-Based**

- **SSE Protocol**: W3C Server-Sent Events specification
- **EventSource API**: Works with browser EventSource client
- **HTTP/1.1 Streaming**: Standard chunked transfer encoding

### 3. **Scalable Architecture**

- **Per-subscriber queues**: Each client gets dedicated asyncio.Queue
- **Async generators**: Memory-efficient streaming (no buffering entire history)
- **Automatic cleanup**: Disconnected clients removed from subscriber list

### 4. **Safe by Default**

- `event_bus_enabled` toggle (default=true)
- `publish_sync()` safe to call from sync code (executor)
- Graceful error handling (failed subscribers skipped)
- No breaking changes (existing tests pass)

---

## Usage Examples

### Frontend JavaScript Client

**Basic connection**:
```javascript
const eventSource = new EventSource('http://localhost:8003/agents/events');

eventSource.addEventListener('run_started', (e) => {
    const data = JSON.parse(e.data);
    console.log(`[${data.agent}] Run ${data.run_id} started`);
    console.log(`Objective: ${data.objective}`);
});

eventSource.addEventListener('run_finished', (e) => {
    const data = JSON.parse(e.data);
    console.log(`[${data.agent}] Run ${data.run_id} finished in ${data.duration_ms}ms`);
    console.log('Artifacts:', data.artifacts);
});

eventSource.addEventListener('run_failed', (e) => {
    const data = JSON.parse(e.data);
    console.error(`[${data.agent}] Run ${data.run_id} failed: ${data.error}`);
});

// Close connection when done
eventSource.close();
```

**React component** (live run tracker):
```javascript
import { useEffect, useState } from 'react';

function AgentRunMonitor() {
    const [runs, setRuns] = useState([]);
    
    useEffect(() => {
        const eventSource = new EventSource('/agents/events');
        
        eventSource.addEventListener('run_started', (e) => {
            const data = JSON.parse(e.data);
            setRuns(prev => [...prev, {
                run_id: data.run_id,
                agent: data.agent,
                status: 'running',
                started_at: new Date(data.timestamp * 1000)
            }]);
        });
        
        eventSource.addEventListener('run_finished', (e) => {
            const data = JSON.parse(e.data);
            setRuns(prev => prev.map(r => 
                r.run_id === data.run_id 
                    ? { ...r, status: 'succeeded', duration_ms: data.duration_ms }
                    : r
            ));
        });
        
        eventSource.addEventListener('run_failed', (e) => {
            const data = JSON.parse(e.data);
            setRuns(prev => prev.map(r => 
                r.run_id === data.run_id 
                    ? { ...r, status: 'failed', error: data.error }
                    : r
            ));
        });
        
        return () => eventSource.close();
    }, []);
    
    return (
        <div>
            <h2>Active Agent Runs ({runs.filter(r => r.status === 'running').length})</h2>
            <ul>
                {runs.map(run => (
                    <li key={run.run_id}>
                        {run.agent}: {run.status}
                        {run.duration_ms && ` (${run.duration_ms}ms)`}
                        {run.error && ` - ${run.error}`}
                    </li>
                ))}
            </ul>
        </div>
    );
}
```

### Python Client

**Using httpx** (async):
```python
import asyncio
import httpx
import json

async def monitor_agent_runs():
    async with httpx.AsyncClient() as client:
        async with client.stream('GET', 'http://localhost:8003/agents/events') as response:
            async for line in response.aiter_lines():
                if line.startswith('event:'):
                    event_type = line.split(':', 1)[1].strip()
                elif line.startswith('data:'):
                    data = json.loads(line.split(':', 1)[1].strip())
                    print(f"[{event_type}] {data['agent']} - {data['run_id']}")
                    
                    if event_type == 'run_finished':
                        print(f"  Duration: {data['duration_ms']}ms")
                    elif event_type == 'run_failed':
                        print(f"  Error: {data['error']}")

asyncio.run(monitor_agent_runs())
```

### cURL Testing

**Watch events in terminal**:
```bash
curl -N http://localhost:8003/agents/events
```

**Trigger run in another terminal**:
```bash
curl -X POST http://localhost:8003/agents/warehouse.health/run \
  -H "Content-Type: application/json" \
  -d '{"objective":"test SSE","dry_run":true}'
```

**Expected SSE output**:
```
event: run_started
id: abc-123-def
data: {"run_id":"abc-123-def","agent":"warehouse.health","timestamp":1735689600.5,"objective":"test SSE","plan":{...}}

event: run_finished
id: abc-123-def
data: {"run_id":"abc-123-def","agent":"warehouse.health","timestamp":1735689601.2,"status":"succeeded","artifacts":{...},"duration_ms":750.3}
```

---

## Implementation Stats

| Category | Count | Details |
|----------|-------|---------|
| **Files Created** | 3 | `events/__init__.py`, `events/bus.py`, `routers/agents_events.py` |
| **Files Modified** | 2 | `agents/executor.py`, `main.py` |
| **Lines of Code** | ~280 | Bus: 155, SSE router: 57, Executor changes: 40, Main: 2 |
| **Event Types** | 4 | run_started, run_log, run_finished, run_failed |
| **New Endpoint** | 1 | `GET /agents/events` |

**Event Payload Size**: 200-500 bytes/event (JSON data)

---

## Testing Strategy

### Unit Tests

**EventBus**:
```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_event_bus_subscribe():
    bus = EventBus()
    
    # Subscribe and collect events
    events = []
    async def collect_events():
        async for event in bus.subscribe():
            events.append(event)
            if len(events) >= 2:
                break
    
    # Publish events
    await asyncio.gather(
        collect_events(),
        bus.publish(AgentEvent(...)),
        bus.publish(AgentEvent(...))
    )
    
    assert len(events) == 2

@pytest.mark.asyncio
async def test_event_bus_publish_sync():
    bus = EventBus()
    event = AgentEvent(event_type="test", ...)
    
    bus.publish_sync(event)  # Should not raise
    await asyncio.sleep(0.1)  # Let event loop process
    
    # Event should be delivered to subscribers

def test_agent_event_to_sse():
    event = AgentEvent(
        event_type="run_started",
        run_id="test-123",
        agent="warehouse.health",
        timestamp=1234567890.5,
        data={"objective": "test"}
    )
    
    sse = event.to_sse()
    
    assert "event: run_started" in sse
    assert "id: test-123" in sse
    assert '"objective":"test"' in sse
    assert sse.endswith("\n\n")  # SSE spec requires double newline
```

**Executor Integration**:
```python
def test_executor_emits_run_started():
    bus = EventBus()
    executor = Executor(store, auditor, event_bus_enabled=True)
    executor.event_bus = bus  # Inject test bus
    
    published_events = []
    bus.publish_sync = lambda e: published_events.append(e)
    
    executor.execute(plan, handler)
    
    assert any(e.event_type == "run_started" for e in published_events)
    assert any(e.event_type == "run_finished" for e in published_events)

def test_executor_event_bus_disabled():
    executor = Executor(store, auditor, event_bus_enabled=False)
    
    # Execute should work without event bus
    run = executor.execute(plan, handler)
    assert run["status"] == "succeeded"
```

### Integration Tests

**SSE Endpoint**:
```python
from fastapi.testclient import TestClient
import json

def test_agents_events_endpoint():
    client = TestClient(app)
    
    with client.stream("GET", "/agents/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
        
        # Trigger agent run in background
        run_response = client.post("/agents/warehouse.health/run", json={
            "objective": "test",
            "dry_run": True
        })
        run_id = run_response.json()["run_id"]
        
        # Collect events from stream
        events = []
        for line in response.iter_lines():
            if line.startswith(b"event:"):
                event_type = line.decode().split(":", 1)[1].strip()
            elif line.startswith(b"data:"):
                data = json.loads(line.decode().split(":", 1)[1])
                events.append((event_type, data))
                
                if event_type in ["run_finished", "run_failed"]:
                    break
        
        # Verify events received
        assert len(events) >= 2
        assert events[0][0] == "run_started"
        assert events[0][1]["run_id"] == run_id
        assert events[-1][0] in ["run_finished", "run_failed"]
```

**End-to-End**:
```python
@pytest.mark.asyncio
async def test_full_sse_workflow():
    # 1. Subscribe to events
    event_source = httpx.AsyncClient()
    response = await event_source.get("/agents/events", stream=True)
    
    # 2. Trigger agent run
    run_response = await httpx.post("/agents/warehouse.health/run", json={
        "objective": "e2e test",
        "dry_run": True
    })
    run_id = run_response.json()["run_id"]
    
    # 3. Collect events
    events = []
    async for line in response.aiter_lines():
        # Parse SSE format
        ...
        if event_type == "run_finished":
            break
    
    # 4. Verify complete lifecycle
    assert events[0]["event_type"] == "run_started"
    assert events[0]["data"]["run_id"] == run_id
    assert events[-1]["event_type"] == "run_finished"
    assert events[-1]["data"]["duration_ms"] > 0
```

---

## Configuration

**Environment Variables**:
```bash
# No new configuration required
# Event bus is always available when API starts
```

**Disable events** (testing):
```python
from app.agents.executor import Executor

executor = Executor(
    run_store,
    auditor,
    event_bus_enabled=False  # Disable SSE events
)
```

**Production Recommendations**:

1. **Connection limits**: Configure nginx/reverse proxy for long-lived connections
   ```nginx
   location /agents/events {
       proxy_buffering off;
       proxy_cache off;
       proxy_read_timeout 3600s;
       proxy_send_timeout 3600s;
   }
   ```

2. **Client reconnection**: Implement exponential backoff in clients
   ```javascript
   let retryDelay = 1000;
   function connectSSE() {
       const es = new EventSource('/agents/events');
       es.onerror = () => {
           es.close();
           setTimeout(() => {
               retryDelay = Math.min(retryDelay * 2, 30000);
               connectSSE();
           }, retryDelay);
       };
       es.onopen = () => { retryDelay = 1000; };
   }
   ```

3. **Load balancing**: Use sticky sessions for SSE endpoints
   ```nginx
   upstream api {
       ip_hash;  # Sticky sessions
       server api1:8003;
       server api2:8003;
   }
   ```

4. **Monitoring**: Track active SSE connections
   ```python
   from prometheus_client import Gauge
   
   sse_connections = Gauge('sse_connections', 'Active SSE connections')
   
   # Update on subscribe/unsubscribe
   sse_connections.set(event_bus.subscriber_count)
   ```

---

## Next Steps (Remaining PRs)

### PR4: Warehouse Health Agent v2
- Real parity computation (ES vs BQ counts)
- Freshness SLO checks (30min threshold)
- Auto-remediation with allow_actions flag
- Enhanced error reporting

### PR5: CI Integration Lane
- Split test jobs: unit (mock) vs integration (real)
- Add Elasticsearch service to CI
- Secrets gating for real provider tests

### PR6: Complete Documentation
- `AGENTS_QUICKSTART.md` - Getting started guide
- `AGENTS_OBSERVABILITY.md` - Metrics, logs, SSE, dashboards
- `RUNBOOK_WAREHOUSE_HEALTH.md` - Operations guide

---

## Migration Notes

### Breaking Changes
- **None**: This is a pure addition

### Backward Compatibility
- All existing agents work without changes
- Tests still pass (event_bus_enabled optional)
- No API changes to existing endpoints

### Dependencies
- **New**: None (uses stdlib asyncio)
- **Python**: Requires Python 3.7+ (async generators)

### Rollout Plan
1. ✅ Deploy code (backward compatible)
2. ✅ Verify `/agents/events` endpoint accessible
3. ✅ Test SSE connection: `curl -N http://localhost:8003/agents/events`
4. ✅ Trigger agent run and observe events
5. ⏳ Update frontend to consume SSE (Phase 2 PR6)
6. ⏳ Monitor SSE connection metrics (Phase 2 PR6)

---

## Files Changed

**Created**:
- `services/api/app/events/__init__.py` (10 lines)
- `services/api/app/events/bus.py` (155 lines)
- `services/api/app/routers/agents_events.py` (57 lines)

**Modified**:
- `services/api/app/agents/executor.py` (+40 lines) - Event emission
- `services/api/app/main.py` (+2 lines) - Wire SSE router

**Total**: 5 files, ~280 lines of code

---

## Success Metrics

**Must Have**:
- [x] EventBus with async subscribe/publish
- [x] AgentEvent with SSE formatting
- [x] GET /agents/events SSE endpoint
- [x] Executor emits run_started, run_finished, run_failed
- [x] All existing tests pass
- [x] No breaking changes

**Verification**:
```bash
# Terminal 1: Subscribe to events
curl -N http://localhost:8003/agents/events

# Terminal 2: Trigger agent run
curl -X POST http://localhost:8003/agents/warehouse.health/run \
  -H "Content-Type: application/json" \
  -d '{"objective":"test SSE","dry_run":true}'
```

**Expected Output** (Terminal 1):
```
event: run_started
id: abc-123-def
data: {"run_id":"abc-123-def","agent":"warehouse.health","timestamp":1735689600.5,...}

event: run_finished
id: abc-123-def
data: {"run_id":"abc-123-def","status":"succeeded","duration_ms":125.5,...}
```

✅ **PR3 Complete**: Real-time agent run updates via SSE operational
