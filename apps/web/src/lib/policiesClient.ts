/**
 * Phase 6: Policy stats API client
 * 
 * Fetches per-user policy performance metrics from /api/policy/stats
 */

export type PolicyStat = {
  policy_id: number
  name: string
  precision: number
  approved: number
  rejected: number
  fired: number
}

export async function fetchPolicyStats(): Promise<PolicyStat[]> {
  const r = await fetch('/api/policy/stats')
  if (!r.ok) throw new Error('Failed to load policy stats')
  return r.json()
}
