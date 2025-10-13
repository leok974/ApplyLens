# Approvals Tray - Grouped UI Specification

This document defines the JSON structure and React component interfaces for rendering grouped approval items in the UI.

## Overview

The Approvals Tray groups proposed email actions by policy and sender domain, allowing users to approve, reject, or execute actions in bulk. This improves UX by reducing decision fatigue when reviewing many similar actions.

## Data Model

### TypeScript Interfaces

```typescript
// ui/types/approvals.ts

export type ApprovalStatus = "proposed" | "approved" | "rejected" | "executed";

export interface ApprovalItem {
  id?: number;                // DB row id if persisted
  email_id: string;           // Gmail message ID
  action: "archive" | "unsubscribe" | "quarantine" | "label" | "create_reminder";
  policy_id: string;          // Policy that generated this action
  confidence: number;         // 0..1 confidence score
  rationale?: string;         // Human-readable explanation
  params?: Record<string, unknown>;  // Action-specific parameters
  status?: ApprovalStatus;    // Current status
  sender_domain?: string;     // For grouping
  subject?: string;           // For UI preview
}

export interface ApprovalGroup {
  group_id: string;           // Unique identifier: `${policy_id}:${sender_domain}`
  title: string;              // Human-readable group label
  policy_id: string;          // Policy that generated these actions
  sender_domain?: string;     // Optional domain for grouping
  count: number;              // Number of items in group
  confidence_avg: number;     // Average confidence across items
  items: ApprovalItem[];      // Individual approval items
  actions: Array<"approve_all" | "reject_all" | "execute_all">;
}
```text

## API Response Format

### Endpoint: `GET /approvals/grouped`

```json
{
  "groups": [
    {
      "group_id": "unsubscribe-stale:news.example.com",
      "title": "Unsubscribe · news.example.com",
      "policy_id": "unsubscribe-stale",
      "sender_domain": "news.example.com",
      "count": 12,
      "confidence_avg": 0.93,
      "actions": ["approve_all", "reject_all", "execute_all"],
      "items": [
        {
          "email_id": "e1",
          "action": "unsubscribe",
          "policy_id": "unsubscribe-stale",
          "confidence": 0.95,
          "rationale": "no opens in 60d",
          "params": {
            "headers": {
              "List-Unsubscribe": "<https://ex.com/u?1>"
            }
          },
          "subject": "Daily News Digest"
        },
        {
          "email_id": "e2",
          "action": "unsubscribe",
          "policy_id": "unsubscribe-stale",
          "confidence": 0.92,
          "params": {
            "headers": {
              "List-Unsubscribe": "<https://ex.com/u?2>"
            }
          },
          "subject": "Weekly Newsletter"
        }
      ]
    },
    {
      "group_id": "promo-expired-archive:*",
      "title": "Archive expired promotions",
      "policy_id": "promo-expired-archive",
      "count": 8,
      "confidence_avg": 0.9,
      "actions": ["approve_all", "reject_all", "execute_all"],
      "items": [
        {
          "email_id": "p1",
          "action": "archive",
          "policy_id": "promo-expired-archive",
          "confidence": 0.9,
          "rationale": "expired 3 days ago",
          "subject": "Flash Sale - 50% Off"
        }
      ]
    }
  ]
}
```text

## React Component

### Minimal Implementation

```tsx
// ui/components/ApprovalsTray.tsx

import { ApprovalGroup, ApprovalItem } from "../types/approvals";

interface ApprovalsTrayProps {
  groups: ApprovalGroup[];
  onApproveAll: (group: ApprovalGroup) => void;
  onRejectAll: (group: ApprovalGroup) => void;
  onExecuteAll: (group: ApprovalGroup) => void;
}

export default function ApprovalsTray({
  groups,
  onApproveAll,
  onRejectAll,
  onExecuteAll
}: ApprovalsTrayProps) {
  return (
    <div className="space-y-4">
      {groups.map(g => (
        <div key={g.group_id} className="rounded-2xl shadow p-4 bg-white">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold">
              {g.title}
              <span className="text-sm opacity-70 ml-2">({g.count})</span>
            </h3>
            <div className="space-x-2">
              <button
                onClick={() => onApproveAll(g)}
                className="px-3 py-1 rounded bg-green-600 text-white hover:bg-green-700"
              >
                Approve all
              </button>
              <button
                onClick={() => onRejectAll(g)}
                className="px-3 py-1 rounded bg-gray-600 text-white hover:bg-gray-700"
              >
                Reject all
              </button>
              <button
                onClick={() => onExecuteAll(g)}
                className="px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
              >
                Execute
              </button>
            </div>
          </div>
          
          <ul className="divide-y">
            {g.items.map((it, idx) => (
              <li key={it.email_id + idx} className="py-2">
                <div className="flex items-center justify-between">
                  <div className="truncate">
                    <div className="text-sm font-medium">
                      {it.subject || it.email_id}
                    </div>
                    <div className="text-xs opacity-70">
                      {it.action} · {it.policy_id} · conf {Math.round(it.confidence * 100)}%
                    </div>
                    {it.rationale && (
                      <div className="text-xs text-gray-600 mt-1">
                        {it.rationale}
                      </div>
                    )}
                  </div>
                  {/* Per-item actions if needed */}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
```text

## Backend Implementation

### Grouping Logic

```python
# app/routers/approvals.py

from typing import Dict, List
from collections import defaultdict

def group_approvals(approvals: List[dict]) -> List[dict]:
    """
    Group approval items by policy_id and sender_domain.
    
    Args:
        approvals: List of approval dictionaries
        
    Returns:
        List of approval groups
    """
    groups = defaultdict(list)
    
    for approval in approvals:
        policy_id = approval.get("policy_id", "unknown")
        sender_domain = approval.get("sender_domain", "*")
        
        # Create group key
        group_key = f"{policy_id}:{sender_domain}"
        groups[group_key].append(approval)
    
    # Build group objects
    result = []
    for group_key, items in groups.items():
        policy_id, sender_domain = group_key.split(":", 1)
        
        # Calculate average confidence
        confidences = [item.get("confidence", 0) for item in items]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Generate title
        action = items[0].get("action", "action")
        if sender_domain != "*":
            title = f"{action.title()} · {sender_domain}"
        else:
            title = f"{action.title()} (multiple senders)"
        
        result.append({
            "group_id": group_key,
            "title": title,
            "policy_id": policy_id,
            "sender_domain": sender_domain if sender_domain != "*" else None,
            "count": len(items),
            "confidence_avg": avg_confidence,
            "items": items,
            "actions": ["approve_all", "reject_all", "execute_all"]
        })
    
    # Sort by count (most items first)
    result.sort(key=lambda g: g["count"], reverse=True)
    
    return result


@router.get("/approvals/grouped")
async def get_grouped_approvals(status: str = "proposed"):
    """
    Get approval items grouped by policy and sender domain.
    
    Args:
        status: Filter by status (default: "proposed")
        
    Returns:
        Dictionary with "groups" key containing list of ApprovalGroup
    """
    # Get all approvals with status
    rows = approvals_get(status=status, limit=1000)
    
    # Enrich with sender_domain and subject from ES if needed
    # (In production, you'd join with emails or query ES)
    approvals = [dict(r) for r in rows]
    
    # Group by policy and sender
    groups = group_approvals(approvals)
    
    return {"groups": groups}
```text

## Usage Examples

### Frontend - Fetch and Display

```typescript
// Fetch grouped approvals
const response = await fetch('/approvals/grouped?status=proposed');
const data = await response.json();

// Render in React
<ApprovalsTray
  groups={data.groups}
  onApproveAll={async (group) => {
    const ids = group.items.map(i => i.id);
    await fetch('/approvals/approve', {
      method: 'POST',
      body: JSON.stringify({ ids }),
      headers: { 'Content-Type': 'application/json' }
    });
    // Refresh groups
  }}
  onRejectAll={async (group) => {
    const ids = group.items.map(i => i.id);
    await fetch('/approvals/reject', {
      method: 'POST',
      body: JSON.stringify({ ids }),
      headers: { 'Content-Type': 'application/json' }
    });
  }}
  onExecuteAll={async (group) => {
    const ids = group.items.map(i => i.id);
    await fetch('/approvals/execute', {
      method: 'POST',
      body: JSON.stringify({ ids }),
      headers: { 'Content-Type': 'application/json' }
    });
  }}
/>
```text

### Backend - Create Grouped Actions

```python
# Example: Policy engine proposes actions
from app.logic.policy_engine import apply_policies
from app.db import approvals_bulk_insert

# Get emails to evaluate
emails = await find_unsubscribe_candidates(days=60)

# Apply policies
actions = []
for email in emails:
    proposed = apply_policies(email, policies=[unsubscribe_policy])
    actions.extend(proposed)

# Bulk insert
rows = [
    {
        "email_id": a.email_id,
        "action": a.action,
        "policy_id": a.policy_id,
        "confidence": a.confidence,
        "rationale": a.rationale,
        "params": a.params
    }
    for a in actions
]
approvals_bulk_insert(rows)

# Later, fetch grouped
groups = await get_grouped_approvals(status="proposed")
# Returns grouped structure ready for UI
```text

## Elasticsearch Dashboard Queries

### ES|QL: Bills Due in Next 7 Days by Sender

```esql
FROM emails_v1
| WHERE category == "bills"
  AND (
    dates < now() + INTERVAL 7 days
    OR expires_at < now() + INTERVAL 7 days
  )
| STATS due_count = count() BY sender_domain
| SORT due_count DESC
| LIMIT 20
```text

### ES|QL: Overdue Bills by Sender

```esql
FROM emails_v1
| WHERE category == "bills"
  AND (
    dates < now()
    OR expires_at < now()
  )
| STATS overdue_count = count() BY sender_domain
| SORT overdue_count DESC
| LIMIT 20
```text

### ES|QL: Approval Actions by Policy

```esql
FROM actions_audit_v1
| WHERE status == "executed"
| STATS executed_count = count() BY policy_id
| SORT executed_count DESC
```text

### ES|QL: Average Confidence by Policy

```esql
FROM actions_audit_v1
| WHERE status == "approved"
| STATS avg_confidence = AVG(confidence) BY policy_id
| SORT avg_confidence DESC
```text

## UI States and Error Handling

### Loading State

```tsx
{isLoading ? (
  <div className="flex justify-center p-8">
    <div className="spinner">Loading approvals...</div>
  </div>
) : (
  <ApprovalsTray groups={groups} {...handlers} />
)}
```text

### Empty State

```tsx
{groups.length === 0 ? (
  <div className="text-center p-8 text-gray-600">
    <p>No pending approvals</p>
    <p className="text-sm mt-2">
      Actions will appear here when policies detect opportunities
    </p>
  </div>
) : (
  <ApprovalsTray groups={groups} {...handlers} />
)}
```text

### Error State

```tsx
{error ? (
  <div className="bg-red-50 border border-red-200 rounded p-4">
    <p className="text-red-700">Failed to load approvals</p>
    <button
      onClick={refetch}
      className="mt-2 text-sm text-red-600 underline"
    >
      Try again
    </button>
  </div>
) : (
  <ApprovalsTray groups={groups} {...handlers} />
)}
```text

## Performance Considerations

### Pagination

For large approval lists, implement pagination in the grouping endpoint:

```python
@router.get("/approvals/grouped")
async def get_grouped_approvals(
    status: str = "proposed",
    page: int = 1,
    page_size: int = 10
):
    # Get total count
    total_rows = approvals_count(status=status)
    
    # Get page of results
    offset = (page - 1) * page_size
    rows = approvals_get(status=status, limit=page_size, offset=offset)
    
    # Group
    groups = group_approvals([dict(r) for r in rows])
    
    return {
        "groups": groups,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total_rows,
            "total_pages": (total_rows + page_size - 1) // page_size
        }
    }
```text

### Caching

Cache grouped approvals for frequently accessed status values:

```python
from functools import lru_cache
from time import time

_cache = {}
_cache_ttl = 60  # seconds

def get_cached_groups(status: str):
    now = time()
    if status in _cache:
        cached_at, groups = _cache[status]
        if now - cached_at < _cache_ttl:
            return groups
    
    # Fetch fresh
    groups = fetch_and_group_approvals(status)
    _cache[status] = (now, groups)
    return groups
```text

## Security Notes

1. **Authorization**: Ensure users can only approve/reject/execute their own approvals
2. **Rate Limiting**: Implement rate limits on bulk operations to prevent abuse
3. **Audit Trail**: All approval actions should be logged to `actions_audit_v1` index
4. **Validation**: Validate that approval IDs exist and belong to the authenticated user

## Future Enhancements

1. **Smart Grouping**: Use ML to group similar emails beyond just sender_domain
2. **Preview Mode**: Show email content preview before executing actions
3. **Undo**: Allow users to undo recently executed actions
4. **Scheduling**: Schedule bulk actions for a specific time
5. **Filters**: Add UI filters for action type, confidence threshold, date range
6. **Notifications**: Send digest emails with pending approvals

## Related Documentation

- [Approvals API Documentation](./APPROVALS_API.md)
- [Policy Engine Guide](./POLICY_ENGINE.md)
- [Elasticsearch Schema](./ES_SCHEMA.md)
- [Advanced Features Summary](./ADVANCED_FEATURES_SUMMARY.md)
