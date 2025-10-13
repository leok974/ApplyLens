/**
 * Phase 6: Policy Accuracy Panel
 * 
 * Displays per-user policy performance metrics:
 * - Precision (approved/fired) as a visual bar
 * - Counters for fired, approved, rejected
 * 
 * Shows top 5 most active policies sorted by fired count.
 */
import { useEffect, useState } from 'react'
import { fetchPolicyStats, PolicyStat } from '@/lib/policiesClient'

function PrecisionBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100
  return (
    <div className="h-2 w-full rounded bg-neutral-800">
      <div className="h-2 rounded bg-emerald-600" style={{ width: `${pct}%` }} />
    </div>
  )
}

export default function PolicyAccuracyPanel() {
  const [rows, setRows] = useState<PolicyStat[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      setLoading(true)
      setErr(null)
      const data = await fetchPolicyStats()
      // sort by fired desc, take top 5
      setRows(data.sort((a, b) => (b.fired ?? 0) - (a.fired ?? 0)).slice(0, 5))
    } catch (e: any) {
      setErr(e?.message ?? 'Error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="rounded-2xl border border-neutral-800 p-3 bg-neutral-900">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Policy Accuracy (30d)</h3>
        <button className="text-[11px] underline" onClick={load}>Refresh</button>
      </div>
      {loading && <div className="text-xs opacity-60 mt-2">Loading…</div>}
      {err && <div className="text-xs text-rose-400 mt-2">{err}</div>}
      {!loading && !err && (
        <div className="mt-3 space-y-3">
          {rows.length === 0 && <div className="text-xs opacity-60">No data yet.</div>}
          {rows.map((r) => (
            <div key={r.policy_id} className="text-xs">
              <div className="flex items-center justify-between">
                <div className="truncate pr-2">{r.name || `Policy #${r.policy_id}`}</div>
                <div className="tabular-nums">{Math.round((r.precision ?? 0) * 100)}%</div>
              </div>
              <PrecisionBar value={r.precision ?? 0} />
              <div className="opacity-60 mt-1">fired {r.fired} • approved {r.approved} • rejected {r.rejected}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
