/**
 * Policy Bundles API Client
 * 
 * Provides functions for interacting with the Policy UI Editor backend.
 */

import { API_BASE } from './apiBase'

export interface PolicyRule {
  id: string
  agent: string
  action: string
  effect: 'allow' | 'deny' | 'needs_approval'
  conditions?: Record<string, any>
  reason: string
  priority: number
  enabled: boolean
  budget?: {
    cost: number
    compute: number
    risk: 'low' | 'medium' | 'high'
  }
  tags?: string[]
  metadata?: Record<string, any>
}

export interface PolicyBundle {
  id: number
  version: string
  rules: PolicyRule[]
  notes?: string
  created_by: string
  created_at: string
  active: boolean
  canary_pct: number
  activated_at?: string
  activated_by?: string
  approval_id?: number
  source?: string
  source_signature?: string
  metadata?: Record<string, any>
}

export interface LintAnnotation {
  rule_id?: string
  severity: 'error' | 'warning' | 'info'
  message: string
  line?: number
  suggestion?: string
}

export interface LintResult {
  errors: LintAnnotation[]
  warnings: LintAnnotation[]
  info: LintAnnotation[]
  passed: boolean
  summary: {
    total_rules: number
    error_count: number
    warning_count: number
    info_count: number
    total_issues: number
  }
}

export interface SimResult {
  case_id: string
  matched_rule?: string
  effect: string
  reason: string
  budget?: any
}

export interface SimSummary {
  total_cases: number
  allow_count: number
  deny_count: number
  approval_count: number
  no_match_count: number
  allow_rate: number
  deny_rate: number
  approval_rate: number
  estimated_cost: number
  estimated_compute: number
  breaches: string[]
}

export interface SimResponse {
  summary: SimSummary
  results: SimResult[]
  examples: SimResult[]
}

/**
 * Fetch all policy bundles
 */
export async function fetchBundles(params?: {
  limit?: number
  offset?: number
  active_only?: boolean
}): Promise<{ bundles: PolicyBundle[]; total: number }> {
  const query = new URLSearchParams()
  if (params?.limit) query.append('limit', params.limit.toString())
  if (params?.offset) query.append('offset', params.offset.toString())
  if (params?.active_only) query.append('active_only', 'true')

  const response = await fetch(`${API_BASE}/policy/bundles?${query}`)
  if (!response.ok) {
    throw new Error('Failed to fetch policy bundles')
  }
  return response.json()
}

/**
 * Fetch active bundle
 */
export async function fetchActiveBundle(): Promise<PolicyBundle | null> {
  const response = await fetch(`${API_BASE}/policy/bundles/active`)
  if (response.status === 404) {
    return null
  }
  if (!response.ok) {
    throw new Error('Failed to fetch active bundle')
  }
  return response.json()
}

/**
 * Fetch bundle by ID
 */
export async function fetchBundle(id: number): Promise<PolicyBundle> {
  const response = await fetch(`${API_BASE}/policy/bundles/${id}`)
  if (!response.ok) {
    throw new Error('Failed to fetch bundle')
  }
  return response.json()
}

/**
 * Create new policy bundle
 */
export async function createBundle(data: {
  version: string
  rules: PolicyRule[]
  notes?: string
  created_by: string
  metadata?: Record<string, any>
}): Promise<PolicyBundle> {
  const response = await fetch(`${API_BASE}/policy/bundles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to create bundle')
  }
  return response.json()
}

/**
 * Update policy bundle (draft only)
 */
export async function updateBundle(
  id: number,
  data: Partial<{
    rules: PolicyRule[]
    notes: string
    metadata: Record<string, any>
  }>
): Promise<PolicyBundle> {
  const response = await fetch(`${API_BASE}/policy/bundles/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to update bundle')
  }
  return response.json()
}

/**
 * Delete policy bundle (draft only)
 */
export async function deleteBundle(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/policy/bundles/${id}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to delete bundle')
  }
}

/**
 * Lint policy rules
 */
export async function lintRules(rules: PolicyRule[]): Promise<LintResult> {
  const response = await fetch(`${API_BASE}/policy/lint`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rules }),
  })
  if (!response.ok) {
    throw new Error('Failed to lint rules')
  }
  return response.json()
}

/**
 * Simulate policy rules
 */
export async function simulateRules(params: {
  rules: PolicyRule[]
  dataset?: 'fixtures' | 'synthetic'
  synthetic_count?: number
  seed?: number
  custom_cases?: any[]
}): Promise<SimResponse> {
  const response = await fetch(`${API_BASE}/policy/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!response.ok) {
    throw new Error('Failed to simulate rules')
  }
  return response.json()
}

/**
 * Export policy bundle
 */
export async function exportBundle(id: number, expiryHours?: number): Promise<any> {
  const query = expiryHours ? `?expiry_hours=${expiryHours}` : ''
  const response = await fetch(`${API_BASE}/policy/bundles/${id}/export${query}`)
  if (!response.ok) {
    throw new Error('Failed to export bundle')
  }
  return response.json()
}

/**
 * Import policy bundle
 */
export async function importBundle(signedBundle: any, importAsVersion?: string): Promise<PolicyBundle> {
  const response = await fetch(`${API_BASE}/policy/bundles/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...signedBundle,
      import_as_version: importAsVersion,
    }),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to import bundle')
  }
  return response.json()
}

/**
 * Activate policy bundle
 */
export async function activateBundle(
  id: number,
  approvalId: number,
  activatedBy: string,
  canaryPct: number = 10
): Promise<PolicyBundle> {
  const response = await fetch(`${API_BASE}/policy/bundles/${id}/activate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      approval_id: approvalId,
      activated_by: activatedBy,
      canary_pct: canaryPct,
    }),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to activate bundle')
  }
  return response.json()
}

/**
 * Promote canary
 */
export async function promoteCanary(id: number, targetPct: number): Promise<PolicyBundle> {
  const response = await fetch(`${API_BASE}/policy/bundles/${id}/promote`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_pct: targetPct }),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to promote canary')
  }
  return response.json()
}

/**
 * Rollback policy bundle
 */
export async function rollbackBundle(
  id: number,
  reason: string,
  rolledBackBy: string,
  createIncident: boolean = true
): Promise<PolicyBundle> {
  const response = await fetch(`${API_BASE}/policy/bundles/${id}/rollback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      reason,
      rolled_back_by: rolledBackBy,
      create_incident: createIncident,
    }),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to rollback bundle')
  }
  return response.json()
}

/**
 * Get canary status
 */
export async function getCanaryStatus(id: number): Promise<any> {
  const response = await fetch(`${API_BASE}/policy/bundles/${id}/canary-status`)
  if (!response.ok) {
    throw new Error('Failed to get canary status')
  }
  return response.json()
}
