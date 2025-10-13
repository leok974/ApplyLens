/**
 * API Client for Phase 4 Agentic Actions & Approval Loop
 * 
 * Provides functions to:
 * - Fetch pending actions for the tray
 * - Approve/reject actions
 * - Propose new actions
 * - Manage policies (CRUD)
 */

import { API_BASE } from './apiBase'

export type ActionType =
  | "label_email"
  | "archive_email"
  | "move_to_folder"
  | "unsubscribe_via_header"
  | "create_calendar_event"
  | "create_task"
  | "block_sender"
  | "quarantine_attachment"

export type ProposedAction = {
  id: number
  email_id: number
  action: ActionType
  params: Record<string, any>
  confidence: number
  rationale: {
    confidence: number
    narrative: string
    reasons?: string[]
    features?: Record<string, any>
  }
  policy_id?: number
  policy_name?: string
  status: "pending" | "approved" | "rejected" | "executed" | "failed"
  reviewed_by?: string
  reviewed_at?: string
  created_at: string
  // Email details (joined)
  email_subject?: string
  email_sender?: string
  email_received_at?: string
}

export type Policy = {
  id: number
  name: string
  enabled: boolean
  priority: number
  condition: Record<string, any>
  action: ActionType
  confidence_threshold: number
  created_at: string
  updated_at: string
}

export type PolicyCreate = {
  name: string
  enabled?: boolean
  priority?: number
  condition: Record<string, any>
  action: ActionType
  confidence_threshold?: number
}

export type PolicyUpdate = {
  name?: string
  enabled?: boolean
  priority?: number
  condition?: Record<string, any>
  action?: ActionType
  confidence_threshold?: number
}

/**
 * Fetch pending actions for the tray UI
 * @param limit Maximum number of actions to return (default 50)
 */
export async function fetchTray(limit: number = 50): Promise<ProposedAction[]> {
  const r = await fetch(`${API_BASE}/actions/tray?limit=${limit}`)
  if (!r.ok) throw new Error(`Failed to fetch tray: ${r.statusText}`)
  return r.json()
}

/**
 * Approve an action and execute it
 * @param id Action ID
 * @param screenshotDataUrl Optional base64 PNG screenshot (data:image/png;base64,...)
 */
export async function approveAction(
  id: number,
  screenshotDataUrl?: string
): Promise<{ ok: boolean; outcome: string; error?: string }> {
  const r = await fetch(`${API_BASE}/actions/${id}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ screenshot_data_url: screenshotDataUrl }),
  })
  if (!r.ok) throw new Error(`Failed to approve action: ${r.statusText}`)
  return r.json()
}

/**
 * Reject an action (will be audited as noop)
 * @param id Action ID
 */
export async function rejectAction(id: number): Promise<{ ok: boolean }> {
  const r = await fetch(`${API_BASE}/actions/${id}/reject`, {
    method: "POST",
  })
  if (!r.ok) throw new Error(`Failed to reject action: ${r.statusText}`)
  return r.json()
}

/**
 * Create a policy from this action ("Always do this" button)
 * @param id Action ID
 * @param features Rationale features to use for policy condition
 */
export async function alwaysDoThis(
  id: number,
  features: Record<string, any>
): Promise<{ ok: boolean; policy_id: number }> {
  const r = await fetch(`${API_BASE}/actions/${id}/always`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rationale_features: features }),
  })
  if (!r.ok) throw new Error(`Failed to create always policy: ${r.statusText}`)
  return r.json()
}

/**
 * Propose actions for emails matching policies
 * @param options Either email_ids or query with optional limit
 */
export async function proposeActions(options: {
  email_ids?: number[]
  query?: string
  limit?: number
}): Promise<{ created: number[]; count: number }> {
  const r = await fetch("/api/actions/propose", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options),
  })
  if (!r.ok) throw new Error(`Failed to propose actions: ${r.statusText}`)
  return r.json()
}

/**
 * List all policies
 * @param enabledOnly If true, only return enabled policies
 */
export async function listPolicies(enabledOnly: boolean = false): Promise<Policy[]> {
  const r = await fetch(`${API_BASE}/actions/policies?enabled_only=${enabledOnly}`)
  if (!r.ok) throw new Error(`Failed to list policies: ${r.statusText}`)
  return r.json()
}

/**
 * Create a new policy
 */
export async function createPolicy(policy: PolicyCreate): Promise<Policy> {
  const r = await fetch(`${API_BASE}/actions/policies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(policy),
  })
  if (!r.ok) throw new Error(`Failed to create policy: ${r.statusText}`)
  return r.json()
}

/**
 * Update an existing policy
 */
export async function updatePolicy(id: number, updates: PolicyUpdate): Promise<Policy> {
  const r = await fetch(`${API_BASE}/actions/policies/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  })
  if (!r.ok) throw new Error(`Failed to update policy: ${r.statusText}`)
  return r.json()
}

/**
 * Delete a policy
 */
export async function deletePolicy(id: number): Promise<{ ok: boolean }> {
  const r = await fetch(`${API_BASE}/actions/policies/${id}`, {
    method: "DELETE",
  })
  if (!r.ok) throw new Error(`Failed to delete policy: ${r.statusText}`)
  return r.json()
}

/**
 * Test a policy against emails
 * @param id Policy ID
 * @param options Either email_ids or limit
 */
export async function testPolicy(
  id: number,
  options?: { email_ids?: number[]; limit?: number }
): Promise<{ matches: number[]; count: number }> {
  const r = await fetch(`${API_BASE}/actions/policies/${id}/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options || {}),
  })
  if (!r.ok) throw new Error(`Failed to test policy: ${r.statusText}`)
  return r.json()
}
