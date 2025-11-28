# API Reference - Phase 5.4 Interventions

**Complete REST API documentation for interventions system.**

---

## Base URL

```
http://localhost:8000/api
```

Production: `https://api.applylens.com/api`

---

## Authentication

All endpoints require authentication (implementation pending).

```http
Authorization: Bearer <token>
```

---

## Incidents API

### **List Incidents**

```http
GET /incidents
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | all | Filter by status: `open`, `acknowledged`, `mitigated`, `resolved`, `closed` |
| `severity` | string | all | Filter by severity: `sev1`, `sev2`, `sev3`, `sev4` |
| `kind` | string | all | Filter by kind: `invariant`, `budget`, `planner` |
| `limit` | integer | 50 | Max results (1-100) |
| `offset` | integer | 0 | Pagination offset |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/incidents?status=open&severity=sev1&limit=10"
```

**Response:** `200 OK`
```json
{
  "incidents": [
    {
      "id": 123,
      "kind": "invariant",
      "key": "INV_data_freshness_inbox",
      "severity": "sev1",
      "status": "open",
      "summary": "Data freshness violation for inbox.triage",
      "details": {
        "invariant": {
          "id": "data_freshness_inbox",
          "threshold": 300,
          "actual": 1800
        }
      },
      "playbooks": ["rerun_eval", "rerun_dbt"],
      "issue_url": "https://github.com/org/repo/issues/456",
      "assigned_to": null,
      "acknowledged_by": null,
      "created_at": "2025-10-17T10:00:00Z",
      "updated_at": "2025-10-17T10:00:00Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

---

### **Get Incident**

```http
GET /incidents/{id}
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Incident ID |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/incidents/123"
```

**Response:** `200 OK`
```json
{
  "id": 123,
  "kind": "invariant",
  "key": "INV_data_freshness_inbox",
  "severity": "sev1",
  "status": "open",
  "summary": "Data freshness violation for inbox.triage",
  "details": {...},
  "playbooks": ["rerun_eval", "rerun_dbt"],
  "issue_url": "https://github.com/org/repo/issues/456",
  "metadata": {
    "agent": "inbox.triage",
    "auto_created": true
  },
  "assigned_to": null,
  "acknowledged_by": null,
  "acknowledged_at": null,
  "mitigated_at": null,
  "resolved_at": null,
  "closed_at": null,
  "created_at": "2025-10-17T10:00:00Z",
  "updated_at": "2025-10-17T10:00:00Z"
}
```

**Errors:**
- `404 Not Found`: Incident not found

---

### **Acknowledge Incident**

```http
POST /incidents/{id}/acknowledge
```

**Request Body:**
```json
{
  "acknowledged_by": "engineer@example.com",
  "notes": "Investigating root cause"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/incidents/123/acknowledge" \
  -H "Content-Type: application/json" \
  -d '{"acknowledged_by": "engineer@example.com", "notes": "Investigating"}'
```

**Response:** `200 OK`
```json
{
  "id": 123,
  "status": "acknowledged",
  "acknowledged_by": "engineer@example.com",
  "acknowledged_at": "2025-10-17T10:05:00Z",
  "updated_at": "2025-10-17T10:05:00Z"
}
```

**Errors:**
- `404 Not Found`: Incident not found
- `400 Bad Request`: Invalid status transition

---

### **Mitigate Incident**

```http
POST /incidents/{id}/mitigate
```

**Request Body:**
```json
{
  "notes": "Executed rerun_dbt playbook, quality recovering"
}
```

**Response:** `200 OK`

---

### **Resolve Incident**

```http
POST /incidents/{id}/resolve
```

**Request Body:**
```json
{
  "notes": "Root cause: stale dependencies. Fixed: refreshed packages. Verified: quality at 95%"
}
```

**Response:** `200 OK`

---

### **Close Incident**

```http
POST /incidents/{id}/close
```

**Request Body:**
```json
{
  "notes": "Verified stable for 24 hours, closing"
}
```

**Response:** `200 OK`

---

### **Assign Incident**

```http
POST /incidents/{id}/assign
```

**Request Body:**
```json
{
  "assigned_to": "engineer@example.com"
}
```

**Response:** `200 OK`

---

## Playbooks API

### **List Available Actions**

```http
GET /playbooks/incidents/{id}/actions
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Incident ID |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/playbooks/incidents/123/actions"
```

**Response:** `200 OK`
```json
{
  "incident_id": 123,
  "available_actions": [
    {
      "action_type": "rerun_dbt",
      "display_name": "Re-run DBT Models",
      "description": "Re-run specified dbt models to refresh data",
      "params": {
        "task_id": "string (required)",
        "models": "array[string] (required)",
        "full_refresh": "boolean (optional, default: false)",
        "upstream": "boolean (optional, default: false)",
        "threads": "integer (optional, default: 4)"
      },
      "requires_approval": false,
      "estimated_duration": "10 minutes",
      "estimated_cost": "$0.10"
    },
    {
      "action_type": "clear_cache",
      "display_name": "Clear Elasticsearch Cache",
      "description": "Clear query/request/fielddata caches",
      "params": {
        "index_name": "string (required)",
        "cache_types": "array[string] (optional, default: all)"
      },
      "requires_approval": false,
      "estimated_duration": "5 seconds",
      "estimated_cost": "$0"
    }
  ]
}
```

---

### **Dry-Run Action**

```http
POST /playbooks/incidents/{id}/actions/dry-run
```

**Request Body:**
```json
{
  "action_type": "rerun_dbt",
  "params": {
    "task_id": "task-123",
    "models": ["inbox_emails", "triage_results"],
    "full_refresh": false,
    "upstream": false,
    "threads": 4
  }
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/playbooks/incidents/123/actions/dry-run" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "rerun_dbt",
    "params": {
      "task_id": "task-123",
      "models": ["inbox_emails"],
      "full_refresh": false
    }
  }'
```

**Response:** `200 OK`
```json
{
  "action_type": "rerun_dbt",
  "status": "dry_run_success",
  "message": "Command: dbt run --models inbox_emails --threads 4",
  "details": {
    "command": "dbt run --models inbox_emails --threads 4",
    "models": ["inbox_emails"]
  },
  "estimated_duration": 300,
  "estimated_cost": 0.05,
  "changes": [
    "Will re-run 1 dbt model",
    "Model: inbox_emails",
    "No full refresh (incremental only)"
  ],
  "requires_approval": false
}
```

**Errors:**
- `404 Not Found`: Incident not found
- `400 Bad Request`: Invalid action type or parameters
- `422 Unprocessable Entity`: Parameter validation failed

---

### **Execute Action**

```http
POST /playbooks/incidents/{id}/actions/execute
```

**Request Body:**
```json
{
  "action_type": "rerun_dbt",
  "params": {
    "task_id": "task-123",
    "models": ["inbox_emails"],
    "full_refresh": true
  },
  "approved_by": "engineer@example.com"
}
```

**Note:** `approved_by` is required if action `requires_approval=true`.

**Example:**
```bash
curl -X POST "http://localhost:8000/api/playbooks/incidents/123/actions/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "rerun_dbt",
    "params": {
      "task_id": "task-123",
      "models": ["inbox_emails"],
      "full_refresh": true
    },
    "approved_by": "engineer@example.com"
  }'
```

**Response:** `200 OK`
```json
{
  "action_id": 456,
  "action_type": "rerun_dbt",
  "status": "success",
  "message": "Successfully ran 1 model(s)",
  "details": {
    "models_run": ["inbox_emails"],
    "exit_code": 0
  },
  "estimated_duration": 300,
  "actual_duration": 720,
  "estimated_cost": 0.05,
  "logs_url": "https://logs.example.com/task-123",
  "rollback_available": false,
  "created_at": "2025-10-17T10:10:00Z",
  "completed_at": "2025-10-17T10:22:00Z"
}
```

**Errors:**
- `404 Not Found`: Incident not found
- `400 Bad Request`: Invalid action type or parameters
- `403 Forbidden`: Approval required but not provided
- `422 Unprocessable Entity`: Parameter validation failed
- `500 Internal Server Error`: Action execution failed

---

### **Rollback Action**

```http
POST /playbooks/incidents/{id}/actions/{action_id}/rollback
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Incident ID |
| `action_id` | integer | Action ID to rollback |

**Request Body:**
```json
{
  "approved_by": "engineer@example.com"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/playbooks/incidents/123/actions/456/rollback" \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "engineer@example.com"}'
```

**Response:** `200 OK`
```json
{
  "action_id": 457,
  "action_type": "rollback_planner",
  "status": "success",
  "message": "Rolled back to v1.2.2",
  "rollback_of": 456
}
```

**Errors:**
- `404 Not Found`: Incident or action not found
- `400 Bad Request`: Rollback not available for this action
- `500 Internal Server Error`: Rollback execution failed

---

### **Get Action History**

```http
GET /playbooks/incidents/{id}/actions/history
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | integer | Incident ID |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/playbooks/incidents/123/actions/history"
```

**Response:** `200 OK`
```json
{
  "incident_id": 123,
  "actions": [
    {
      "id": 1,
      "action_type": "rerun_dbt",
      "params": {"models": ["inbox_emails"]},
      "dry_run": true,
      "status": "dry_run_success",
      "approved_by": null,
      "created_at": "2025-10-17T10:00:00Z"
    },
    {
      "id": 2,
      "action_type": "rerun_dbt",
      "params": {"models": ["inbox_emails"], "full_refresh": true},
      "dry_run": false,
      "status": "success",
      "approved_by": "engineer@example.com",
      "result": {
        "actual_duration": 720,
        "logs_url": "https://logs.example.com/123"
      },
      "created_at": "2025-10-17T10:05:00Z"
    }
  ]
}
```

---

## SSE (Server-Sent Events) API

### **Subscribe to Events**

```http
GET /sse/events
```

**Description:** Opens EventSource connection for real-time incident updates.

**Example (JavaScript):**
```javascript
const eventSource = new EventSource('http://localhost:8000/api/sse/events');

eventSource.addEventListener('connected', (event) => {
  console.log('Connected:', JSON.parse(event.data));
});

eventSource.addEventListener('incident_created', (event) => {
  const incident = JSON.parse(event.data);
  console.log('New incident:', incident);
});

eventSource.addEventListener('incident_updated', (event) => {
  const incident = JSON.parse(event.data);
  console.log('Incident updated:', incident);
});

eventSource.addEventListener('action_executed', (event) => {
  const action = JSON.parse(event.data);
  console.log('Action executed:', action);
});

eventSource.addEventListener('heartbeat', (event) => {
  // Keep-alive (every 30 seconds)
});

eventSource.onerror = () => {
  console.error('SSE connection error');
};
```

**Event Types:**

**`connected`:**
```json
{
  "subscriber_id": "abc-123",
  "timestamp": "2025-10-17T10:00:00Z"
}
```

**`incident_created`:**
```json
{
  "id": 123,
  "kind": "invariant",
  "severity": "sev1",
  "status": "open",
  "summary": "Data freshness violation",
  "created_at": "2025-10-17T10:00:00Z"
}
```

**`incident_updated`:**
```json
{
  "id": 123,
  "status": "acknowledged",
  "acknowledged_by": "engineer@example.com",
  "change": "acknowledged"
}
```

**`action_executed`:**
```json
{
  "incident_id": 123,
  "action_id": 456,
  "action_type": "rerun_dbt",
  "status": "success"
}
```

**`heartbeat`:**
```json
{
  "timestamp": "2025-10-17T10:00:30Z"
}
```

---

## Error Responses

### **Standard Error Format**

All errors return:
```json
{
  "error": {
    "code": "not_found",
    "message": "Incident not found",
    "details": {}
  }
}
```

### **Error Codes**

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `not_found` | 404 | Resource not found |
| `bad_request` | 400 | Invalid request format |
| `validation_error` | 422 | Parameter validation failed |
| `forbidden` | 403 | Approval required |
| `internal_error` | 500 | Server error |
| `timeout` | 504 | Operation timeout |

---

## Rate Limiting

**Limits:**
- 1000 requests per hour per IP
- 100 dry-runs per hour per incident
- 10 action executions per hour per incident

**Headers:**
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1634486400
```

**Error:**
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 3600
```

---

## Webhooks (Future)

**Coming in future release:**
- Subscribe to incident events via webhooks
- Configure webhook URLs in settings
- Receive POST requests on incident state changes

---

## SDK Examples

### **Python**

```python
import requests

BASE_URL = "http://localhost:8000/api"

# List open SEV1 incidents
response = requests.get(
    f"{BASE_URL}/incidents",
    params={"status": "open", "severity": "sev1"}
)
incidents = response.json()["incidents"]

# Acknowledge incident
requests.post(
    f"{BASE_URL}/incidents/123/acknowledge",
    json={
        "acknowledged_by": "engineer@example.com",
        "notes": "Investigating"
    }
)

# Dry-run action
response = requests.post(
    f"{BASE_URL}/playbooks/incidents/123/actions/dry-run",
    json={
        "action_type": "rerun_dbt",
        "params": {
            "task_id": "task-123",
            "models": ["inbox_emails"]
        }
    }
)
result = response.json()
print(f"Estimated: {result['estimated_duration']}s, ${result['estimated_cost']}")

# Execute action
requests.post(
    f"{BASE_URL}/playbooks/incidents/123/actions/execute",
    json={
        "action_type": "rerun_dbt",
        "params": {...},
        "approved_by": "engineer@example.com"
    }
)
```

### **JavaScript/TypeScript**

```typescript
const BASE_URL = "http://localhost:8000/api";

// List incidents
const response = await fetch(
  `${BASE_URL}/incidents?status=open&severity=sev1`
);
const { incidents } = await response.json();

// Acknowledge
await fetch(`${BASE_URL}/incidents/123/acknowledge`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    acknowledged_by: "engineer@example.com",
    notes: "Investigating"
  })
});

// SSE subscription
const eventSource = new EventSource(`${BASE_URL}/sse/events`);
eventSource.addEventListener("incident_created", (event) => {
  const incident = JSON.parse(event.data);
  console.log("New incident:", incident);
});
```

### **cURL**

```bash
# List incidents
curl -X GET "http://localhost:8000/api/incidents?status=open"

# Acknowledge
curl -X POST "http://localhost:8000/api/incidents/123/acknowledge" \
  -H "Content-Type: application/json" \
  -d '{"acknowledged_by": "me@example.com"}'

# Dry-run
curl -X POST "http://localhost:8000/api/playbooks/incidents/123/actions/dry-run" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "rerun_dbt",
    "params": {"task_id": "task-123", "models": ["inbox_emails"]}
  }'

# Execute
curl -X POST "http://localhost:8000/api/playbooks/incidents/123/actions/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "rerun_dbt",
    "params": {"task_id": "task-123", "models": ["inbox_emails"]},
    "approved_by": "me@example.com"
  }'
```

---

## Summary

**Endpoints:**
- **Incidents**: 8 endpoints (list, get, acknowledge, mitigate, resolve, close, assign)
- **Playbooks**: 5 endpoints (list actions, dry-run, execute, rollback, history)
- **SSE**: 1 endpoint (event stream)

**For operational guides, see:**
- [INTERVENTIONS_GUIDE.md](./INTERVENTIONS_GUIDE.md)
- [PLAYBOOKS.md](./PLAYBOOKS.md)
- [RUNBOOK_SEVERITY.md](./RUNBOOK_SEVERITY.md)
