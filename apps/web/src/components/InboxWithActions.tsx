import { useEffect, useState } from 'react'
import { searchEmails, explainEmail, actions, SearchHit, ExplainResponse } from '../lib/api'
import { safeFormatDate } from '../lib/date'
import { Alert, AlertDescription } from './ui/alert'
import { Info } from 'lucide-react'

export default function InboxWithActions() {
  const [q, setQ] = useState('')
  const [sender, setSender] = useState('')
  const [label, setLabel] = useState('')
  const [rows, setRows] = useState<SearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [explains, setExplains] = useState<Record<string, ExplainResponse>>({})
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await searchEmails(q || '*', 50)
      setRows(data)
    } catch (err) {
      setError(`Search failed: ${err}`)
    } finally {
      setLoading(false)
    }
  }

  // Initial search on mount
  useEffect(() => {
    run()
  }, [])

  const doExplain = async (id: string | number) => {
    try {
      const docId = String(id)
      const e = await explainEmail(docId)
      setExplains(prev => ({ ...prev, [docId]: e }))
    } catch (err) {
      setError(`Explain failed: ${err}`)
    }
  }

  const doAction = async (action: (id: string) => Promise<any>, docId: string | number, actionName: string) => {
    const id = String(docId)
    setActionLoading(prev => ({ ...prev, [id]: true }))
    setError(null)
    try {
      const result = await action(id)
      setSuccessMsg(`✅ ${result.message || `${actionName} action recorded`}`)
      setTimeout(() => setSuccessMsg(null), 3000)
    } catch (err) {
      setError(`Action failed: ${err}`)
    } finally {
      setActionLoading(prev => ({ ...prev, [id]: false }))
    }
  }

  const btn = (label: string, onClick: () => void, disabled = false) => (
    <button
      className="px-2 py-1 text-xs rounded border hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  )

  return (
    <div className="p-4 grid gap-4">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">📬 Inbox with Quick Actions</h1>
        <p className="text-sm text-gray-600">Search, explain, and take action on emails</p>
      </div>

      {/* Messages */}
      {error && (
        <div className="p-3 rounded bg-red-50 text-red-800 text-sm border border-red-200">
          {error}
        </div>
      )}
      {successMsg && (
        <div className="p-3 rounded bg-green-50 text-green-800 text-sm border border-green-200">
          {successMsg}
        </div>
      )}

      {/* Search Filters */}
      <div className="flex gap-2 flex-wrap">
        <input
          className="border px-3 py-2 rounded w-80 focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Search subject/body…"
          value={q}
          onChange={e => setQ(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && run()}
        />
        <input
          className="border px-3 py-2 rounded w-56 focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Filter: sender domain"
          value={sender}
          onChange={e => setSender(e.target.value)}
        />
        <input
          className="border px-3 py-2 rounded w-56 focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Filter: label"
          value={label}
          onChange={e => setLabel(e.target.value)}
        />
        <button
          className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition font-medium"
          onClick={run}
          disabled={loading}
        >
          {loading ? '⏳ Searching…' : '🔍 Search'}
        </button>
      </div>

      {/* Results Count */}
      <div className="text-sm text-gray-600">
        {loading ? 'Searching...' : `${rows.length} results`}
      </div>

      {/* Email Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b-2 border-gray-300">
              <th className="text-left py-3 px-2 font-semibold text-gray-700">From</th>
              <th className="text-left py-3 px-2 font-semibold text-gray-700">Subject</th>
              <th className="text-left py-3 px-2 font-semibold text-gray-700">Received</th>
              <th className="text-left py-3 px-2 font-semibold text-gray-700">Reason</th>
              <th className="text-left py-3 px-2 font-semibold text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading && (
              <tr>
                <td colSpan={5} className="py-8 text-center text-gray-500">
                  No results found. Try a different search query.
                </td>
              </tr>
            )}
            {rows.map(r => {
              const docId = r.id ? String(r.id) : (r as any).gmail_id || 'unknown'
              const explain = explains[docId]
              const isActionLoading = actionLoading[docId]

              return (
                <tr key={docId} className="border-b border-gray-200 hover:bg-gray-50 align-top">
                  {/* From */}
                  <td className="py-3 px-2 text-sm">
                    <div className="text-gray-700 font-medium">
                      {(r as any).sender_domain || r.sender || r.from_addr || '—'}
                    </div>
                    {r.sender && r.sender !== (r as any).sender_domain && (
                      <div className="text-xs text-gray-500">{r.sender}</div>
                    )}
                  </td>

                  {/* Subject */}
                  <td className="py-3 px-2">
                    <div className="font-medium text-gray-900">{r.subject}</div>
                    {r.labels && r.labels.length > 0 && (
                      <div className="mt-1 flex gap-1 flex-wrap">
                        {r.labels.slice(0, 3).map((lbl, i) => (
                          <span
                            key={i}
                            className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700"
                          >
                            {lbl.replace('CATEGORY_', '')}
                          </span>
                        ))}
                        {r.labels.length > 3 && (
                          <span className="text-xs text-gray-500">+{r.labels.length - 3}</span>
                        )}
                      </div>
                    )}
                  </td>

                  {/* Received */}
                  <td className="py-3 px-2 text-sm text-gray-500">
                    {safeFormatDate(r.received_at) ?? '—'}
                  </td>

                  {/* Reason */}
                  <td className="py-3 px-2">
                    {explain ? (
                      <div className="text-sm">
                        <div className="font-medium text-gray-900">{explain.reason}</div>
                        <div className="text-xs mt-1 text-gray-500">
                          <div>Labels: {explain.evidence.label_heuristics?.join(', ') || 'none'}</div>
                          {explain.evidence.list_unsubscribe && <div>Has unsubscribe link</div>}
                          {explain.evidence.keywords_hit && <div>Promo keywords detected</div>}
                        </div>
                      </div>
                    ) : (
                      <button
                        className="text-xs text-blue-600 hover:underline"
                        onClick={() => doExplain(docId)}
                      >
                        🔍 Explain why
                      </button>
                    )}
                  </td>

                  {/* Actions */}
                  <td className="py-3 px-2">
                    <div className="flex gap-1 flex-wrap">
                      {btn(
                        '📥 Archive',
                        () => doAction(actions.archive, docId, 'Archive'),
                        isActionLoading
                      )}
                      {btn(
                        '✅ Safe',
                        () => doAction(actions.markSafe, docId, 'Mark Safe'),
                        isActionLoading
                      )}
                      {btn(
                        '⚠️ Suspicious',
                        () => doAction(actions.markSuspicious, docId, 'Mark Suspicious'),
                        isActionLoading
                      )}
                      {btn(
                        '🚫 Unsub',
                        () => doAction(actions.unsubscribeDry, docId, 'Unsubscribe'),
                        isActionLoading
                      )}
                    </div>
                    {isActionLoading && (
                      <div className="text-xs text-gray-500 mt-1">Processing...</div>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Info Note */}
      <Alert className="mt-4">
        <Info className="h-4 w-4" />
        <AlertDescription>
          <strong>Dry-run mode:</strong> Quick actions (Archive, Mark Safe/Suspicious, Unsubscribe) are
          recorded to the audit log but don't modify Gmail yet. This is for testing and demonstration purposes.
        </AlertDescription>
      </Alert>
    </div>
  )
}
